import asyncio
import torch
import traceback
import json
import websockets.server
from collections import deque
import threading
import copy
from websockets.exceptions import ConnectionClosed

__version__ = "0.0.2"
__author__ = '(WebSocket version by Gemini)'


class SplatvizNetworkWs:

    def __init__(self, host="127.0.0.1", port=6009):
        self.host = host
        self.port = port
        self.clients = set()
        self._render_requests = deque(maxlen=1) # Only store the latest request
        self.server = None
        self.loop = None

    def is_connected(self):
        """Check if there are any active client connections."""
        return len(self.clients) > 0

    def get_render_request(self):
        if self._render_requests:
            return self._render_requests.popleft()
        return None

    async def _register(self, websocket):
        self.clients.add(websocket)
        print(f"Client connected: {websocket.remote_address}. Total clients: {len(self.clients)}")

    async def _unregister(self, websocket):
        """Unregister a client connection."""
        self.clients.remove(websocket)
        print(f"Client disconnected: {websocket.remote_address}. Total clients: {len(self.clients)}")

    async def _handler(self, websocket, path):
        await self._register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if "heartbeat" in data: # Respond to heartbeats to keep connection alive
                        continue
                    self._render_requests.append(EasyDict(data))
                except json.JSONDecodeError:
                    print("Error: Received invalid JSON message.")
                except Exception as e:
                    print(f"Error processing message: {e}")
        except ConnectionClosed as e:
            print(f"Connection closed with code {e.code}: {e.reason}")
        finally:
            await self._unregister(websocket)

    async def send_rendered_output(self, image_bytes, training_stats_dict):

        if not self.is_connected():
            return
        stats_json = json.dumps(training_stats_dict)
        tasks = []
        for client in self.clients.copy():  # Use copy to avoid modification during iteration
            try:
                tasks.append(asyncio.create_task(client.send(stats_json)))
                if image_bytes is not None:
                    # Convert memoryview to bytes if necessary
                    if isinstance(image_bytes, memoryview):
                        image_data = bytes(image_bytes)
                    else:
                        image_data = image_bytes
                    tasks.append(asyncio.create_task(client.send(image_data)))
                print(f"[DEBUG] Created send tasks for client {client.remote_address}")
            except Exception as e:
                self.clients.discard(client)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(f"[DEBUG] Send tasks completed with {len(results)} results")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"[ERROR] Send task {i} failed: {result}")
        else:
            print(f"[DEBUG] No send tasks created")

    def send_rendered_output_threadsafe(self, image_bytes, training_stats_dict):
        """
        A thread-safe method to call `send_rendered_output` from another thread.
        """
        if self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.send_rendered_output(image_bytes, training_stats_dict),
                    self.loop
                )
                # Wait for completion with timeout
                future.result(timeout=1.0)
                print(f"[DEBUG] Successfully sent rendered output to {len(self.clients)} clients")
            except Exception as e:
                print(f"[ERROR] Failed to send rendered output: {e}")
        else:
            print(f"[ERROR] WebSocket event loop not available, cannot send rendered output")

    def _parse_render_request(self, message):
        """Parses the dictionary from a render request into structured objects."""
        try:
            width = message.resolution_x
            height = message.resolution_y
            
            world_view_transform = torch.reshape(torch.tensor(message.view_matrix, dtype=torch.float32), (4, 4)).cuda()
            world_view_transform[:, 1] = -world_view_transform[:, 1]
            world_view_transform[:, 2] = -world_view_transform[:, 2]
            
            full_proj_transform = torch.reshape(torch.tensor(message.view_projection_matrix, dtype=torch.float32), (4, 4)).cuda()
            full_proj_transform[:, 1] = -full_proj_transform[:, 1]

            custom_cam = MiniCam(
                width, height, message.fov_y, message.fov_x, 
                message.z_near, message.z_far, 
                world_view_transform, full_proj_transform
            )
            
            # The rest of the parameters can be accessed directly from the EasyDict
            message.custom_cam = custom_cam
            return message

        except Exception as e:
            traceback.print_exc()
            print(f"Error parsing render request: {e}")
            return None


    async def start(self):
        """Starts the WebSocket server."""
        try:
            print(f"Starting WebSocket server on ws://{self.host}:{self.port}...")
            self.server = await websockets.server.serve(
                self._handler, 
                self.host, 
                self.port,
                ping_interval=20,  # 发送ping每20秒
                ping_timeout=10,   # ping超时10秒
                close_timeout=10   # 关闭超时10秒
            )
            print(f"WebSocket server started successfully on ws://{self.host}:{self.port}")
            print(f"Server is ready to accept connections...")
            
            # Keep the server running indefinitely
            await self.server.wait_closed()
            
        except OSError as e:
            if e.errno == 10048:  # Windows: Address already in use
                print(f"Error: Port {self.port} is already in use. Please choose a different port.")
            else:
                print(f"WebSocket server OS error: {e}")
            raise
        except Exception as e:
            print(f"WebSocket server error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def start_server_in_thread(self):
        """Utility method to run the server in a background thread."""
        def run_loop():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                print(f"Starting WebSocket server thread on {self.host}:{self.port}")
                self.loop.run_until_complete(self.start())
            except Exception as e:
                print(f"Error in WebSocket server thread: {e}")
                import traceback
                traceback.print_exc()

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        
        # Wait until the loop is created and running
        import time
        max_wait_time = 5.0  # 最多等待5秒
        wait_time = 0.0
        while self.loop is None and wait_time < max_wait_time:
            time.sleep(0.01)
            wait_time += 0.01
        
        if self.loop is None:
            print("Warning: WebSocket server loop not created within timeout")
        else:
            print("WebSocket server thread started successfully.")
        
        return thread


    def render_and_respond_async(self, pipe, gaussians, loss, render, background, iteration, opt):
        """
        An async version of the main render loop integration.
        This would be called from your main training loop.
        """
        request = self.get_render_request()
        if not request:
            return

        parsed_request = self._parse_render_request(request)
        if not parsed_request:
            return

        edit_error = ""
        try:
            net_image_bytes = None
            pipe.convert_SHs_python = parsed_request.shs_python
            pipe.compute_cov3D_python = parsed_request.rot_scale_python
            
            # Note: For security, running exec on arbitrary text is dangerous.
            # Consider a safer way to apply edits if this is exposed to untrusted clients.
            if len(parsed_request.edit_text) > 0:
                gs = copy.deepcopy(gaussians)
                slider = parsed_request.slider
                try:
                    exec(parsed_request.edit_text)
                except Exception as e:
                    edit_error = str(e)
            else:
                gs = gaussians

            if parsed_request.custom_cam:
                with torch.no_grad():
                    net_image = render(parsed_request.custom_cam, gs, pipe, background, parsed_request.scaling_modifier)["render"]
                net_image_bytes = memoryview((torch.clamp(net_image, min=0, max=1.0) * 255).byte().permute(1, 2, 0).contiguous().cpu().numpy())

            training_stats = {
                "loss": loss,
                "iteration": iteration,
                "num_gaussians": gaussians.get_xyz.shape[0],
                "sh_degree": gaussians.active_sh_degree,
                "train_params": vars(opt) if opt else {},
                "error": edit_error,
                "paused": parsed_request.stop_at_value == iteration
            }
            
            # This needs to be awaited
            asyncio.create_task(self.send_rendered_output(net_image_bytes, training_stats))

        except Exception as e:
            print(f"An error occurred during rendering: {e}")
            traceback.print_exc()

class EasyDict(dict):
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        del self[name]


class MiniCam:
    def __init__(self, width, height, fovy, fovx, znear, zfar, world_view_transform, full_proj_transform):
        self.image_width = width
        self.image_height = height
        self.FoVy = fovy
        self.FoVx = fovx
        self.znear = znear
        self.zfar = zfar
        self.world_view_transform = world_view_transform
        self.full_proj_transform = full_proj_transform
        view_inv = torch.inverse(self.world_view_transform)
        self.camera_center = view_inv[3][:3]
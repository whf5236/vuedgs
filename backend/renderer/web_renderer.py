import asyncio
import json
import numpy as np
import torch
import websockets

from gs.scene.cameras import CustomCam
from renderer.base_renderer import Renderer

# A quick note on dependencies:
# This renderer requires the 'websockets' library.
# Please install it using: pip install websockets


class WebRenderer(Renderer):
    """
    A renderer that connects to a backend rendering service via WebSockets.
    This is suitable for communicating with a web-based frontend or a WebSocket server.
    """

    def __init__(self, host, port):
        super().__init__()
        self.uri = f"ws://{host}:{port}"
        self._websocket = None
        print(f"WebRenderer initialized. Will connect to: {self.uri}")

    async def _get_connection(self):
        if self._websocket and self._websocket.open:
            return self._websocket

        try:
            # Set a timeout for the connection attempt
            self._websocket = await asyncio.wait_for(websockets.connect(self.uri), timeout=2.0)
            print(f"Successfully connected to WebSocket server at {self.uri}")
            return self._websocket
        except Exception as e:
            self._websocket = None
            # Do not print error spam. The UI will show a connection message.
            return None

    def _render_impl(self, res, **kwargs):
        """
        Synchronous bridge to the asynchronous rendering implementation.
        This method is called by the synchronous `render` method in the base class.
        It creates a new asyncio event loop to run the async logic.
        """
        try:
            asyncio.run(self._async_render_impl(res, **kwargs))
        except RuntimeError as e:
            # This can happen if an asyncio loop is already running in the thread.
            # In that case, we can try to get the existing loop.
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(self._async_render_impl(res, **kwargs))
            except Exception as async_e:
                res.error = f"Async execution error: {async_e}"


    async def _async_render_impl(
        self,
        res,
        fov,
        edit_text,
        resolution,
        cam_params,
        do_training,
        stop_at_value=-1,
        single_training_step=False,
        slider={},
        img_normalize=False,
        save_ply_path=None,
        **other_args,
    ):
        """
        The core asynchronous rendering logic using WebSockets.
        """
        websocket = await self._get_connection()
        if not websocket:
            res.message = f"Connecting to\n{self.uri}..."
            # Return a blank image while trying to connect
            blank_image = torch.zeros(3, resolution, resolution)
            self._return_image(blank_image, res, normalize=False)
            return

        cam_params = cam_params.to("cuda")
        fov_rad = fov / 360 * 2 * np.pi
        render_cam = CustomCam(resolution, resolution, fovy=fov_rad, fovx=fov_rad, extr=cam_params)

        # Invert all operations from network_gui.py
        world_view_transform = render_cam.world_view_transform.clone()
        world_view_transform[:, 1] = -world_view_transform[:, 1]
        world_view_transform[:, 2] = -world_view_transform[:, 2]

        full_proj_transform = render_cam.full_proj_transform.clone()
        full_proj_transform[:, 1] = -full_proj_transform[:, 1]

        message = {
            "resolution_x": resolution,
            "resolution_y": resolution,
            "train": do_training,
            "fov_y": fov_rad,
            "fov_x": fov_rad,
            "z_near": 0.01,
            "z_far": 10.0,
            "shs_python": False,
            "rot_scale_python": False,
            "keep_alive": True,
            "scaling_modifier": 1,
            "view_matrix": world_view_transform.cpu().numpy().flatten().tolist(),
            "view_projection_matrix": full_proj_transform.cpu().numpy().flatten().tolist(),
            "edit_text": self.sanitize_command(edit_text),
            "slider": slider,
            "single_training_step": single_training_step,
            "stop_at_value": stop_at_value,
        }

        try:
            # 1. Send the rendering request to the server
            await websocket.send(json.dumps(message))

            # 2. Receive the stats/metadata as a JSON message
            stats_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            stats = json.loads(stats_data)

            # 3. Receive the image as a binary message
            image_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            image_np = np.frombuffer(image_data, dtype=np.uint8).reshape(resolution, resolution, 3)
            image = torch.from_numpy(image_np) / 255.0
            image = image.permute(2, 0, 1)

            if len(stats.keys()) > 0:
                res.training_stats = stats
                if "error" in stats and stats["error"]:
                    res.error = res.training_stats["error"]
            
            self._return_image(
                image,
                res,
                normalize=img_normalize,
            )

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            res.error = f"Connection lost. Reconnecting... ({type(e).__name__})"
            await self._close_connection()
            blank_image = torch.zeros(3, resolution, resolution)
            self._return_image(blank_image, res, normalize=False)
        except asyncio.TimeoutError:
            res.error = "Connection timed out. Server may be busy or down."
            await self._close_connection()
            blank_image = torch.zeros(3, resolution, resolution)
            self._return_image(blank_image, res, normalize=False)
        except Exception as e:
            res.error = f"An unexpected error occurred: {e}"
            await self._close_connection()


    async def _close_connection(self):
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

    def __del__(self):
        # Ensure the connection is closed when the object is destroyed
        if self._websocket:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(self._close_connection())
                else:
                    loop.run_until_complete(self._close_connection())
            except Exception:
                # Ignore errors on cleanup
                pass 
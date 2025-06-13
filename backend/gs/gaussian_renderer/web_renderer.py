import asyncio
import json
import numpy as np
import torch
from threading import Thread
import websockets
import websockets.client
import websockets.exceptions  # 添加异常处理模块
import cv2  # 添加OpenCV用于图像压缩

from gs.scene.cameras import CustomCam
from base_renderer import Renderer



class WebRenderer(Renderer):

    def __init__(self, host, port):
        super().__init__()
        self.uri = f"ws://{host}:{port}"
        self._websocket = None

    async def _get_connection(self):
        if self._websocket and self._websocket.open:
            return self._websocket

        try:
            # Set a timeout for the connection attempt
            self._websocket = await asyncio.wait_for(websockets.client.connect(self.uri), timeout=2.0)
            print(f"Successfully connected to WebSocket server at {self.uri}")
            return self._websocket
        except Exception as e:
            self._websocket = None
            # Do not print error spam. The UI will show a connection message.
            return None

    def _render_impl(self, res, **kwargs):

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
        quality='high',  # 新增参数：渲染质量
        is_predictive=False,  # 新增参数：是否是预测性渲染
        **other_args,
    ):
        """
        The core asynchronous rendering logic using WebSockets.
        支持不同质量级别的渲染和预测性渲染
        """
        websocket = await self._get_connection()
        if not websocket:
            res.message = f"Connecting to\n{self.uri}..."
            # Return a blank image while trying to connect
            blank_image = torch.zeros(3, resolution, resolution)
            self._return_image(blank_image, res, normalize=False)
            return

        # 根据质量级别调整分辨率
        actual_resolution = resolution
        if quality == 'low':
            actual_resolution = min(resolution, 400)
        elif quality == 'medium':
            actual_resolution = min(resolution, 600)

        # 根据质量级别调整压缩率
        compression_quality = 90  # 默认高质量
        if quality == 'low':
            compression_quality = 70
        elif quality == 'medium':
            compression_quality = 80

        cam_params = cam_params.to("cuda")
        fov_rad = fov / 360 * 2 * np.pi
        render_cam = CustomCam(actual_resolution, actual_resolution, fovy=fov_rad, fovx=fov_rad, extr=cam_params)

        # Invert all operations from network_gui.py
        world_view_transform = render_cam.world_view_transform.clone()
        world_view_transform[:, 1] = -world_view_transform[:, 1]
        world_view_transform[:, 2] = -world_view_transform[:, 2]

        full_proj_transform = render_cam.full_proj_transform.clone()
        full_proj_transform[:, 1] = -full_proj_transform[:, 1]

        message = {
            "resolution_x": actual_resolution,
            "resolution_y": actual_resolution,
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
            "quality": quality,  # 添加质量参数
            "is_predictive": is_predictive,  # 添加预测性渲染标记
        }

        try:
            # 1. Send the rendering request to the server
            await websocket.send(json.dumps(message))

            # 2. Receive the stats/metadata as a JSON message
            stats_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            stats = json.loads(stats_data)

            # 添加视角参数到统计数据，用于前端缓存
            if is_predictive:
                stats["view_params"] = {
                    "position": cam_params.cpu().numpy().tolist(),
                    "rotation": [fov, 0, 0],  # 简化，实际应该从相机参数计算
                    "fov": fov
                }
                stats["is_predictive"] = True

            # 3. Receive the image as a binary message
            image_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            image_np = np.frombuffer(image_data, dtype=np.uint8).reshape(actual_resolution, actual_resolution, 3)
            
            # 如果实际分辨率与请求分辨率不同，调整图像大小
            if actual_resolution != resolution:
                image_np = cv2.resize(image_np, (resolution, resolution), interpolation=cv2.INTER_LINEAR)
            
            # 如果需要压缩图像（用于发送到前端）
            if hasattr(res, 'need_compressed_image') and res.need_compressed_image:
                compressed_image = self.compress_image(image_np, compression_quality)
                res.compressed_image = compressed_image
            
            # 转换为PyTorch张量
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

    # 添加图像压缩方法
    def compress_image(self, image_np, quality=80):
        """压缩图像为JPEG格式"""
        try:
            success, encoded_image = cv2.imencode('.jpg', image_np, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if success:
                return encoded_image.tobytes()
        except Exception as e:
            print(f"Image compression error: {e}")
        return None

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
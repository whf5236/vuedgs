import re
import traceback
import torch
from utils.dict_util import EasyDict

class Renderer:
    def __init__(self):
        self._device = torch.device("cuda")
        self._pinned_bufs = dict()
        self._is_timing = False
        self._start_event = torch.cuda.Event(enable_timing=True)
        self._end_event = torch.cuda.Event(enable_timing=True)

    def render(self, **args):
        print(f"[DEBUG] 开始渲染，参数: {list(args.keys())}")
        self._is_timing = True
        self._start_event.record(torch.cuda.current_stream(self._device))
        res = EasyDict()
        try:
            with torch.no_grad():
                print(f"[DEBUG] 调用 _render_impl")
                self._render_impl(res, **args)
                print(f"[DEBUG] _render_impl 完成，结果包含: {list(res.keys())}")
        except Exception as e:
            error_msg = "".join(traceback.format_exception(e))
            res.error = error_msg + str(e)
            print(f"[DEBUG] 渲染异常: {str(e)}")
            print(f"[DEBUG] 异常详情: {error_msg}")
        self._end_event.record(torch.cuda.current_stream(self._device))
        
        # 处理渲染结果
        if "image" in res:
            img_shape = res.image.shape if hasattr(res.image, 'shape') else 'unknown'
            print(f"[DEBUG] 图像数据形状: {img_shape}")
            res.image = res.image.cpu().detach().numpy()
            print(f"[DEBUG] 图像转换为 numpy，最终形状: {res.image.shape}")
            print(f"[DEBUG] 图像值范围: {res.image.min():.3f} - {res.image.max():.3f}")
        else:
            print(f"[DEBUG] 警告: 渲染结果中没有图像数据")
            
        if "stats" in res:
            res.stats = res.stats.cpu().detach().numpy()
            print(f"[DEBUG] 统计数据: {res.stats}")
            
        if "error" in res:
            res.error = str(res.error)
            print(f"[DEBUG] 错误信息: {res.error}")
            
        if self._is_timing:
            self._end_event.synchronize()
            res.render_time = self._start_event.elapsed_time(self._end_event) * 1e-3
            print(f"[DEBUG] 渲染耗时: {res.render_time:.3f}s")
            self._is_timing = False
            
        print(f"[DEBUG] 渲染完成，返回结果包含: {list(res.keys())}")
        return res

    @staticmethod
    def sanitize_command(edit_text):
        command = re.sub(";+", ";", edit_text.replace("\n", ";"))
        while command.startswith(";"):
            command = command[1:]
        return command

    def _render_impl(self, **args):
        raise NotImplementedError

    def _load_model(self, path):
        raise NotImplementedError

    @staticmethod
    def _return_image(
        images,
        res: dict,
        normalize: bool,
        use_splitscreen: bool = False,
        highlight_border: bool = False,
        on_top: bool = False,
    ) -> None:

        if not isinstance(images, list):
            images = [images]

        if use_splitscreen:
            img = torch.zeros_like(images[0])
            split_size = img.shape[-1] // len(images)
            offset = 0
            for i in range(len(images)):
                img[..., offset : offset + split_size] = images[i][..., offset : offset + split_size]
                offset += split_size
                if highlight_border and i != len(images) - 1:
                    img[..., offset - 1 : offset] = 1

        elif on_top:
            mask = torch.mean(images[1], dim=0)
            img = images[0] * (1 - mask) + images[1] * mask
        else:
            img = torch.concat(images, dim=2)

        res.stats = torch.stack([img.mean(), img.std()])

        # Scale and convert to uint8.
        if normalize:
            img = img / img.norm(float("inf"), dim=[1, 2], keepdim=True).clip(1e-8, 1e8)
        img = (img * 255).clamp(0, 255).to(torch.uint8).permute(1, 2, 0)
        res.image = img

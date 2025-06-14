import os
import torch
import sys
import uuid
import traceback
from random import randint
from utils.loss_utils import l1_loss, ssim
from gaussian_renderer import render
from scene import Scene, GaussianModel
from utils.general_utils import safe_state
from tqdm import tqdm
from argparse import ArgumentParser, Namespace
from arguments import ModelParams, PipelineParams, OptimizationParams
from splatviz_network import SplatvizNetworkWs


class GaussianTrainer:
    """
    高斯训练器类，封装了3D高斯点的训练流程
    """
    def __init__(self, args=None):
        """
        初始化训练器
        
        Args:
            args: 命令行参数对象，如果为None则使用默认参数
        """
        self.args = args
        self.model_params = None
        self.opt_params = None
        self.pipeline_params = None
        self.log_file_path = None
        
        # 如果没有提供参数，使用默认参数
        if args is None:
            self.args, self.model_params, self.opt_params, self.pipeline_params = self.parse_arguments()
        else:
            # 从提供的参数中提取模型、优化和管道参数
            parser = ArgumentParser()
            lp = ModelParams(parser)
            op = OptimizationParams(parser)
            pp = PipelineParams(parser)
            self.model_params = lp.extract(args)
            self.opt_params = op.extract(args)
            self.pipeline_params = pp.extract(args)
        
        # 设置输出路径
        self.args = self.prepare_output_and_logger(self.args)
        self.log_file_path = os.path.join(self.args.model_path, "train_script_crash.log")

    @staticmethod
    def parse_arguments():
        """
        解析命令行参数
        
        Returns:
            tuple: (args, model_params, opt_params, pipeline_params)
        """
        parser = ArgumentParser(description="Training script parameters")
        lp = ModelParams(parser)
        op = OptimizationParams(parser)
        pp = PipelineParams(parser)
        parser.add_argument('--ip', type=str, default="127.0.0.1")
        parser.add_argument('--port', type=int, default=6009)
        parser.add_argument('--debug_from', type=int, default=-1)
        parser.add_argument('--detect_anomaly', action='store_true', default=False)
        parser.add_argument("--test_iterations", nargs="+", type=int, default=[7_000, 30_000])
        parser.add_argument("--save_iterations", nargs="+", type=int, default=[7_000, 30_000])
        parser.add_argument("--quiet", action="store_true")
        parser.add_argument('--disable_viewer', action='store_true', default=False)
        parser.add_argument("--checkpoint_iterations", nargs="+", type=int, default=[])
        parser.add_argument("--start_checkpoint", type=str, default=None)
        
        args = parser.parse_args(sys.argv[1:])
        args.save_iterations.append(args.iterations)
        
        return args, lp, op, pp

    @staticmethod
    def prepare_output_and_logger(args):
        """
        准备输出目录和日志记录器
        
        Args:
            args: 命令行参数对象
            
        Returns:
            args: 更新后的参数对象
        """
        if not args.model_path:
            if os.getenv('OAR_JOB_ID'):
                unique_str = os.getenv('OAR_JOB_ID')
            else:
                unique_str = str(uuid.uuid4())
            # 确保unique_str不为None再进行下标操作
            if unique_str:
                args.model_path = os.path.join("./output/", unique_str[0:10])
            else:
                args.model_path = os.path.join("./output/", "default")
            
        # 设置输出文件夹
        print("Output folder: {}".format(args.model_path))
        os.makedirs(args.model_path, exist_ok=True)
        with open(os.path.join(args.model_path, "cfg_args"), 'w') as cfg_log_f:
            cfg_log_f.write(str(Namespace(**vars(args))))

        return args

    def train(self):
        """
        执行训练流程
        
        Returns:
            bool: 训练是否成功完成
        """
        try:
            safe_state(self.args.quiet)

            self.training(
                self.model_params, 
                self.opt_params, 
                self.pipeline_params, 
                self.args.test_iterations, 
                self.args.save_iterations, 
                self.args.checkpoint_iterations, 
                self.args.start_checkpoint, 
                self.args.debug_from, 
                self.args.ip, 
                self.args.port
            )

            # 训练完成
            print("\nTraining complete.")
            return True
            
        except Exception as e:
            # 创建详细的错误报告
            error_report = f"FATAL ERROR in gs/train.py\n\n"
            error_report += f"Exception Type: {type(e).__name__}\n"
            error_report += f"Exception Args: {e.args}\n\n"
            error_report += "------------------- TRACEBACK -------------------\n"
            error_report += traceback.format_exc()
            error_report += "\n------------------- ARGUMENTS -------------------\n"
            error_report += str(self.args)
            
            # 将报告写入崩溃日志
            with open(self.log_file_path, 'w') as f:
                f.write(error_report)
                
            # 同时输出到stderr以便父进程捕获
            print(error_report, file=sys.stderr)
            
            return False

    def training(self, dataset, opt, pipe, testing_iterations, saving_iterations, checkpoint_iterations, checkpoint, debug_from, ip, port):
        """
        训练过程的核心实现
        
        Args:
            dataset: 数据集参数
            opt: 优化参数
            pipe: 渲染管道参数
            testing_iterations: 测试迭代次数列表
            saving_iterations: 保存模型的迭代次数列表
            checkpoint_iterations: 保存检查点的迭代次数列表
            checkpoint: 起始检查点路径
            debug_from: 开始调试的迭代次数
            ip: WebSocket服务器IP
            port: WebSocket服务器端口
        """
        first_iter = 0
        gaussians = GaussianModel(dataset.sh_degree)
        scene = Scene(dataset, gaussians)
        gaussians.training_setup(opt)
        if checkpoint:
            (model_params, first_iter) = torch.load(checkpoint)
            gaussians.restore(model_params, opt)

        bg_color = [1, 1, 1] if dataset.white_background else [0, 0, 0]
        background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")

        iter_start = torch.cuda.Event(enable_timing=True)
        iter_end = torch.cuda.Event(enable_timing=True)

        viewpoint_stack = scene.getTrainCameras().copy()
        ema_loss_for_log = 0.0
        progress_bar = tqdm(range(first_iter, opt.iterations), desc="Training progress")
        first_iter += 1
        network = SplatvizNetworkWs()
        
        for iteration in range(first_iter, opt.iterations + 1):
            network.render_and_respond_async(pipe, gaussians, ema_loss_for_log, render, background, iteration, opt)
            gaussians.update_learning_rate(iteration)
            if iteration % 1000 == 0:
                gaussians.oneupSHdegree()
            if not viewpoint_stack:
                viewpoint_stack = scene.getTrainCameras().copy()
            viewpoint_cam = viewpoint_stack.pop(randint(0, len(viewpoint_stack)-1))
            # 渲染
            if (iteration - 1) == debug_from:
                pipe.debug = True
            bg = torch.rand((3), device="cuda") if opt.random_background else background
            render_pkg = render(viewpoint_cam, gaussians, pipe, bg)
            image, viewspace_point_tensor, visibility_filter, radii = render_pkg["render"], render_pkg["viewspace_points"], render_pkg["visibility_filter"], render_pkg["radii"]
            gt_image = viewpoint_cam.original_image.cuda()
            Ll1 = l1_loss(image, gt_image)
            ssim_value = ssim(image, gt_image)
            loss = (1.0 - opt.lambda_dssim) * Ll1 + opt.lambda_dssim * (1.0 - ssim_value)
            loss.backward()

            with torch.no_grad():
                ema_loss_for_log = 0.4 * loss.item() + 0.6 * ema_loss_for_log        
                if iteration % 10 == 0:
                    progress_bar.set_postfix({"Loss": f"{ema_loss_for_log:.{7}f}"})
                    progress_bar.update(10)
                if iteration == opt.iterations:
                    progress_bar.close()       
                    print("\n[ITER {}] Saving Gaussians".format(iteration))
                    scene.save(iteration)
                if iteration < opt.densify_until_iter:
                    # 跟踪图像空间中的最大半径以进行修剪
                    gaussians.max_radii2D[visibility_filter] = torch.max(gaussians.max_radii2D[visibility_filter], radii[visibility_filter])
                    gaussians.add_densification_stats(viewspace_point_tensor, visibility_filter)

                    if iteration > opt.densify_from_iter and iteration % opt.densification_interval == 0:
                        size_threshold = 20 if iteration > opt.opacity_reset_interval else None
                        gaussians.densify_and_prune(opt.densify_grad_threshold, 0.005, scene.cameras_extent, size_threshold, radii)
                    
                    if iteration % opt.opacity_reset_interval == 0 or (dataset.white_background and iteration == opt.densify_from_iter):
                        gaussians.reset_opacity()

                # 优化器步骤
                if iteration < opt.iterations:
                    if gaussians.optimizer is not None:
                        gaussians.optimizer.step()
                        gaussians.optimizer.zero_grad(set_to_none=True)

                if (iteration in checkpoint_iterations):
                    print("\n[ITER {}] Saving Checkpoint".format(iteration))
                    torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")

                iter_end.record(torch.cuda.current_stream())
                torch.cuda.synchronize()
                iter_time = iter_start.elapsed_time(iter_end)
                if iteration % 100 == 0:
                    print(f"Iteration {iteration} took {iter_time:.2f} ms")


# 如果作为主程序运行，创建训练器并开始训练
def main():
    trainer = GaussianTrainer()
    trainer.train()


if __name__ == "__main__":
    main() 
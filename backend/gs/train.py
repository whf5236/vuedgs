#
# Copyright (C) 2023, Inria
# GRAPHDECO research group, https://team.inria.fr/graphdeco
# All rights reserved.
#
# This software is free for non-commercial, research and evaluation use 
# under the terms of the LICENSE.md file.
#
# For inquiries contact  george.drettakis@inria.fr
#

import os
import torch
from random import randint
from utils.loss_utils import l1_loss, ssim
from gaussian_renderer import render
import sys
from scene import Scene, GaussianModel
from utils.general_utils import safe_state
import uuid
from tqdm import tqdm
from utils.image_utils import psnr
from argparse import ArgumentParser, Namespace
from arguments import ModelParams, PipelineParams, OptimizationParams
from splatviz_network import SplatvizNetworkWs
import copy
import traceback
import numpy as np
import threading
import time
from scene.cameras import CustomCam
from PIL import Image
import io
import math
import copy


def training(dataset, opt, pipe, testing_iterations, saving_iterations, checkpoint_iterations, checkpoint, debug_from, ip, port):
    first_iter = 0
    gaussians = GaussianModel(dataset.sh_degree)
    scene = Scene(dataset, gaussians)
    gaussians.training_setup(opt)
    if checkpoint:
        (model_params, first_iter) = torch.load(checkpoint)
        gaussians.restore(model_params, opt)

    bg_color = [1, 1, 1] if dataset.white_background else [0, 0, 0]
    background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")

    iter_start = torch.cuda.Event(enable_timing = True)
    iter_end = torch.cuda.Event(enable_timing = True)

    # Correctly initialize max_radii2D if it's not done in the model
    if gaussians.max_radii2D is None:
        gaussians.max_radii2D = torch.zeros((gaussians.get_xyz.shape[0]), device="cuda")

    viewpoint_stack = scene.getTrainCameras().copy()
    ema_loss_for_log = 0.0

    progress_bar = tqdm(range(first_iter, opt.iterations), desc="Training progress")
    first_iter += 1

    # 1. 在循环开始前，实例化并启动 WebSocket 服务器
    print(f"Initializing SplatvizNetwork WebSocket server on {ip}:{port}")
    network = SplatvizNetworkWs(host=ip, port=port)
    server_thread = network.start_server_in_thread()
    
    # 等待服务器启动完成
    import time
    print("Waiting for WebSocket server to start...")
    time.sleep(2)  # 等待2秒确保服务器完全启动
    print("WebSocket server should be ready for connections.")

    # 创建并启动持续渲染器
    continuous_renderer = ContinuousRenderer(network, gaussians, pipe, background, scene)
    continuous_renderer.start_continuous_rendering()

    try:
        for iteration in range(first_iter, opt.iterations + 1):
            iter_start.record(torch.cuda.current_stream())
                
            gaussians.update_learning_rate(iteration)

            # Every 1000 its we increase the levels of SH up to a maximum degree
            if iteration % 1000 == 0:
                gaussians.oneupSHdegree()

            # Pick a random Camera
            if not viewpoint_stack:
                viewpoint_stack = scene.getTrainCameras().copy()

            viewpoint_cam = viewpoint_stack.pop(randint(0, len(viewpoint_stack)-1))
            # Render
            if (iteration - 1) == debug_from:
                pipe.debug = True

            bg = torch.rand((3), device="cuda") if opt.random_background else background

            render_pkg = render(viewpoint_cam, gaussians, pipe, bg)
            image, viewspace_point_tensor, visibility_filter, radii = render_pkg["render"], render_pkg["viewspace_points"], render_pkg["visibility_filter"], render_pkg["radii"]

            # Loss
            gt_image = viewpoint_cam.original_image.cuda()
            Ll1 = l1_loss(image, gt_image)
     
            ssim_value = ssim(image, gt_image)

            loss = (1.0 - opt.lambda_dssim) * Ll1 + opt.lambda_dssim * (1.0 - ssim_value)

            loss.backward()

            with torch.no_grad():
                # Progress bar
                ema_loss_for_log = 0.4 * loss.item() + 0.6 * ema_loss_for_log
                
                # 更新持续渲染器的训练统计信息
                continuous_renderer.update_training_stats(iteration, ema_loss_for_log)
                
                if iteration % 10 == 0:
                    progress_bar.set_postfix({"Loss": f"{ema_loss_for_log:.{7}f}"})
                    progress_bar.update(10)
                if iteration == opt.iterations:
                    progress_bar.close()       
                    print("\n[ITER {}] Saving Gaussians".format(iteration))
                    scene.save(iteration)

                # Densification
                if iteration < opt.densify_until_iter:
                    # Keep track of max radii in image-space for pruning
                    gaussians.max_radii2D[visibility_filter] = torch.max(gaussians.max_radii2D[visibility_filter], radii[visibility_filter])
                    gaussians.add_densification_stats(viewspace_point_tensor, visibility_filter)

                    if iteration > opt.densify_from_iter and iteration % opt.densification_interval == 0:
                        size_threshold = 20 if iteration > opt.opacity_reset_interval else None
                        gaussians.densify_and_prune(opt.densify_grad_threshold, 0.005, scene.cameras_extent, size_threshold, radii)
                    
                    if iteration % opt.opacity_reset_interval == 0 or (dataset.white_background and iteration == opt.densify_from_iter):
                        gaussians.reset_opacity()

                # Optimizer step
                if iteration < opt.iterations:
                    if gaussians.optimizer is not None:
                        gaussians.optimizer.step()
                        gaussians.optimizer.zero_grad(set_to_none = True)

                if (iteration in checkpoint_iterations):
                    print("\n[ITER {}] Saving Checkpoint".format(iteration))
                    torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")

                iter_end.record(torch.cuda.current_stream())
                torch.cuda.synchronize()
                iter_time = iter_start.elapsed_time(iter_end)
                if iteration % 100 == 0:
                    print(f"Iteration {iteration} took {iter_time:.2f} ms")
    
    finally:
        # 确保停止持续渲染器
        continuous_renderer.stop_continuous_rendering()
        print("训练完成，持续渲染器已停止")

def prepare_output_and_logger(args):    
    if not args.model_path:
        if os.getenv('OAR_JOB_ID'):
            unique_str=os.getenv('OAR_JOB_ID')
        else:
            unique_str = str(uuid.uuid4())
        args.model_path = os.path.join("./output/", unique_str[0:10])
        
    # Set up output folder
    print("Output folder: {}".format(args.model_path))
    os.makedirs(args.model_path, exist_ok = True)
    with open(os.path.join(args.model_path, "cfg_args"), 'w') as cfg_log_f:
        cfg_log_f.write(str(Namespace(**vars(args))))

    # Create Tensorboard writer


if __name__ == "__main__":
    # Set up command line argument parser
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
    parser.add_argument("--start_checkpoint", type=str, default = None)
    args = parser.parse_args(sys.argv[1:])
    args.save_iterations.append(args.iterations)
    
    # Robust error handling with "black box" logging
    # Ensure model_path exists for logging purposes
    if not args.model_path:
        if os.getenv('OAR_JOB_ID'):
            unique_str=os.getenv('OAR_JOB_ID')
        else:
            unique_str = str(uuid.uuid4())
        args.model_path = os.path.join("./output/", unique_str[0:10])
    os.makedirs(args.model_path, exist_ok = True)
    log_file_path = os.path.join(args.model_path, "train_script_crash.log")

    try:
        print("Optimizing " + args.model_path)

        # Initialize system state (RNG)
        safe_state(args.quiet)

        training(lp.extract(args), op.extract(args), pp.extract(args), args.test_iterations, args.save_iterations, args.checkpoint_iterations, args.start_checkpoint, args.debug_from, args.ip, args.port)

        # All done
        print("\nTraining complete.")
        
    except Exception as e:
        # Create a detailed error report
        error_report = f"FATAL ERROR in gs/train.py\n\n"
        error_report += f"Exception Type: {type(e).__name__}\n"
        error_report += f"Exception Args: {e.args}\n\n"
        error_report += "------------------- TRACEBACK -------------------\n"
        error_report += traceback.format_exc()
        error_report += "\n------------------- ARGUMENTS -------------------\n"
        error_report += str(args)
        
        # Write the report to the crash log
        with open(log_file_path, 'w') as f:
            f.write(error_report)
            
        # Also print to stderr for the parent process to capture
        print(error_report, file=sys.stderr)
        
        sys.exit(1) # Ensure a non-zero exit code

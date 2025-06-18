import os
import sys
import logging
from argparse import ArgumentParser
import shutil
import subprocess
from PIL import Image

# 配置日志记录
logging.basicConfig(
    level=logging.DEBUG,  # 使用DEBUG级别以获取更多信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('convert_debug.log')  # 同时保存到文件
    ]
)
logger = logging.getLogger('convert')

logger.info(f"Python version: {sys.version}")
logger.info(f"Operating system: {sys.platform}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Script path: {os.path.abspath(__file__)}")

# This Python script is based on the shell converter script provided in the MipNerF 360 repository.
parser = ArgumentParser("Colmap converter")
parser.add_argument("--no_gpu", action='store_true')
parser.add_argument("--skip_matching", action='store_true')
parser.add_argument("--source_path", "-s", required=True, type=str)
parser.add_argument("--output_path", "-o", type=str, help="Output directory path. If not specified, results will be saved in the source directory.")
parser.add_argument("--camera", default="OPENCV", type=str)
parser.add_argument("--resize", action="store_true")
args = parser.parse_args()
# 使用内置的COLMAP路径
colmap_command = "colmap"
use_gpu = 1 if not args.no_gpu else 0

# 如果没有指定输出路径，使用源路径
output_path = args.output_path if args.output_path else args.source_path


# 检查路径是否存在
if not os.path.exists(args.source_path):
    logger.error(f"源路径不存在: {args.source_path}")
    exit(1)

# 检查源路径中是否有图像文件夹
source_images = os.path.join(args.source_path, "images")
if not os.path.exists(source_images) or not os.path.isdir(source_images):
    logger.error(f"源路径中没有images文件夹: {source_images}")
    exit(1)

# 检查源图像文件夹中是否有图像
image_files = [f for f in os.listdir(source_images) if os.path.isfile(os.path.join(source_images, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))]
if not image_files:
    logger.error(f"源图像文件夹中没有图像文件: {source_images}")
    exit(1)
# 确保输出目录存在
os.makedirs(output_path, exist_ok=True)
logger.info(f"已创建输出目录: {output_path}")

if not args.skip_matching:
    # 创建输出目录结构
    os.makedirs(output_path + "/distorted/sparse", exist_ok=True)

    # 确保输出目录中有 images 文件夹
    images_dir = output_path + "/images"
    os.makedirs(images_dir, exist_ok=True)

    # 如果输出路径与源路径不同，复制图片并检查尺寸
    if output_path != args.source_path:
        logger.info("Copying images from source to output directory...")
        source_images = os.path.join(args.source_path, "images")
        if os.path.exists(source_images) and os.path.isdir(source_images):
            # 首先检查所有图像的尺寸是否一致
            image_sizes = {}
            for img_file in os.listdir(source_images):
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    source_img = os.path.join(source_images, img_file)
                    try:
                        with Image.open(source_img) as img:
                            width, height = img.size
                            image_sizes[img_file] = (width, height)
                    except Exception as e:
                        logger.error(f"无法读取图像 {source_img}: {str(e)}")

            # 检查是否所有图像尺寸一致
            if len(set(image_sizes.values())) > 1:
                # 找出最常见的尺寸
                size_counts = {}
                for size in image_sizes.values():
                    size_counts[size] = size_counts.get(size, 0) + 1

                most_common_size = max(size_counts.items(), key=lambda x: x[1])[0]
                logger.info(f"将所有图像调整为最常见的尺寸: {most_common_size}")

                # 复制并调整图像尺寸
                for img_file in os.listdir(source_images):
                    if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        source_img = os.path.join(source_images, img_file)
                        dest_img = os.path.join(images_dir, img_file)

                        try:
                            with Image.open(source_img) as img:
                                if img.size != most_common_size:
                                    logger.info(f"调整图像 {img_file} 从 {img.size} 到 {most_common_size}")
                                    resized_img = img.resize(most_common_size, Image.LANCZOS)
                                    resized_img.save(dest_img, quality=95)
                                else:
                                    # 尺寸已经正确，直接复制
                                    if not os.path.exists(dest_img):
                                        shutil.copy2(source_img, dest_img)
                        except Exception as e:
                            logger.error(f"处理图像 {source_img} 失败: {str(e)}")
            else:
                # 所有图像尺寸一致，直接复制
                logger.info("所有图像尺寸一致，直接复制")
                for img_file in os.listdir(source_images):
                    source_img = os.path.join(source_images, img_file)
                    dest_img = os.path.join(images_dir, img_file)
                    if os.path.isfile(source_img) and not os.path.exists(dest_img):
                        shutil.copy2(source_img, dest_img)

    ## Feature extraction
    feat_extracton_cmd = colmap_command + " feature_extractor "\
        "--database_path " + output_path + "/distorted/database.db \
        --image_path " + images_dir + " \
        --ImageReader.single_camera 1 \
        --ImageReader.camera_model " + args.camera + " \
        --SiftExtraction.use_gpu " + str(use_gpu) + " \
        --SiftExtraction.max_num_features 8192 \
        --SiftExtraction.first_octave -1 \
        --SiftExtraction.num_octaves 4 \
        --SiftExtraction.peak_threshold 0.004"

    logger.info(f"Running feature extraction: {feat_extracton_cmd}")
    try:
        # 使用 subprocess 模块执行命令，以便更好地捕获错误
        process = subprocess.Popen(
            feat_extracton_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        exit_code = process.returncode

        # 记录输出
        if stdout:
            logger.info(f"Feature extraction stdout: {stdout}")
        if stderr:
            logger.warning(f"Feature extraction stderr: {stderr}")

        if exit_code != 0:
            logger.error(f"Feature extraction failed with code {exit_code}. Exiting.")
            logger.error(f"Error message: {stderr}")
            exit(exit_code)
    except Exception as e:
        logger.error(f"Exception during feature extraction: {str(e)}")
        exit(1)

    ## Feature matching
    feat_matching_cmd = colmap_command + " exhaustive_matcher \
        --database_path " + output_path + "/distorted/database.db \
        --SiftMatching.use_gpu " + str(use_gpu) + " \
        --SiftMatching.max_ratio 0.9 \
        --SiftMatching.max_distance 0.8 \
        --SiftMatching.cross_check 1"

    logger.info(f"Running feature matching: {feat_matching_cmd}")
    try:
        # 使用 subprocess 模块执行命令，以便更好地捕获错误
        process = subprocess.Popen(
            feat_matching_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        exit_code = process.returncode

        # 记录输出
        if stdout:
            logger.info(f"Feature matching stdout: {stdout}")
        if stderr:
            logger.warning(f"Feature matching stderr: {stderr}")

        if exit_code != 0:
            logger.error(f"Feature matching failed with code {exit_code}. Exiting.")
            logger.error(f"Error message: {stderr}")
            exit(exit_code)
    except Exception as e:
        logger.error(f"Exception during feature matching: {str(e)}")
        exit(1)

    ### Bundle adjustment
    # The default Mapper tolerance is unnecessarily large,
    # decreasing it speeds up bundle adjustment steps.
    mapper_cmd = (colmap_command + " mapper \
        --database_path " + output_path + "/distorted/database.db \
        --image_path "  + images_dir + " \
        --output_path "  + output_path + "/distorted/sparse \
        --Mapper.ba_global_function_tolerance=0.000001")
    logger.info(f"Running mapper: {mapper_cmd}")
    try:
        # 使用 subprocess 模块执行命令，以便更好地捕获错误
        process = subprocess.Popen(
            mapper_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        exit_code = process.returncode

        # 记录输出
        if stdout:
            logger.info(f"Mapper stdout: {stdout}")
        if stderr:
            logger.warning(f"Mapper stderr: {stderr}")

        if exit_code != 0:
            logger.error(f"Mapper failed with code {exit_code}. Exiting.")
            logger.error(f"Error message: {stderr}")
            exit(exit_code)
    except Exception as e:
        logger.error(f"Exception during mapper: {str(e)}")
        exit(1)

### Image undistortion
## We need to undistort our images into ideal pinhole intrinsics.
logger.info("准备进行图像去畸变处理")

# 再次检查图像尺寸与相机参数是否匹配
try:
    # 读取相机参数
    cameras_file = os.path.join(output_path, "distorted/sparse/0/cameras.txt")
    if os.path.exists(cameras_file):
        logger.info(f"读取相机参数文件: {cameras_file}")
        camera_params = {}
        with open(cameras_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) >= 4:  # 相机ID, 模型, 宽度, 高度, ...
                    camera_id = parts[0]
                    width = int(parts[2])
                    height = int(parts[3])
                    camera_params[camera_id] = (width, height)
                    logger.info(f"相机 {camera_id} 参数: 宽度={width}, 高度={height}")

        # 读取图像与相机的对应关系
        images_file = os.path.join(output_path, "distorted/sparse/0/images.txt")
        if os.path.exists(images_file):
            logger.info(f"读取图像参数文件: {images_file}")
            image_cameras = {}
            with open(images_file, 'r') as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    if line.startswith('#') or not line.strip():
                        continue
                    if line_num % 2 == 1:  # 图像行
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            image_id = parts[0]
                            camera_id = parts[8]
                            image_name = parts[9]
                            image_cameras[image_name] = camera_id
                            logger.info(f"图像 {image_name} 使用相机 {camera_id}")

            # 检查图像尺寸与相机参数是否匹配
            for img_file in os.listdir(images_dir):
                if img_file in image_cameras:
                    camera_id = image_cameras[img_file]
                    if camera_id in camera_params:
                        expected_width, expected_height = camera_params[camera_id]
                        img_path = os.path.join(images_dir, img_file)
                        try:
                            with Image.open(img_path) as img:
                                actual_width, actual_height = img.size
                                if actual_width != expected_width or actual_height != expected_height:
                                    logger.warning(f"图像 {img_file} 尺寸 ({actual_width}x{actual_height}) 与相机参数 ({expected_width}x{expected_height}) 不匹配，调整图像尺寸")
                                    resized_img = img.resize((expected_width, expected_height), Image.LANCZOS)
                                    resized_img.save(img_path, quality=95)
                        except Exception as e:
                            logger.error(f"处理图像 {img_path} 失败: {str(e)}")
except Exception as e:
    logger.error(f"检查图像尺寸与相机参数时出错: {str(e)}")

# 执行图像去畸变
img_undist_cmd = (colmap_command + " image_undistorter \
    --image_path " + images_dir + " \
    --input_path " + output_path + "/distorted/sparse/0 \
    --output_path " + output_path + "\
    --output_type COLMAP")
logger.info(f"Running image undistorter: {img_undist_cmd}")
try:
    # 使用 subprocess 模块执行命令，以便更好地捕获错误
    process = subprocess.Popen(
        img_undist_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    # 记录输出
    if stdout:
        logger.info(f"Image undistorter stdout: {stdout}")
    if stderr:
        logger.warning(f"Image undistorter stderr: {stderr}")

    if exit_code != 0:
        logger.error(f"Image undistorter failed with code {exit_code}. Exiting.")
        logger.error(f"Error message: {stderr}")
        exit(exit_code)
except Exception as e:
    logger.error(f"Exception during image undistorter: {str(e)}")
    exit(1)

files = os.listdir(output_path + "/sparse")
os.makedirs(output_path + "/sparse/0", exist_ok=True)
# Copy each file from the source directory to the destination directory
for file in files:
    if file == '0':
        continue
    source_file = os.path.join(output_path, "sparse", file)
    destination_file = os.path.join(output_path, "sparse", "0", file)
    shutil.move(source_file, destination_file)

if(args.resize):
    print("Copying and resizing...")

    # Resize images.
    os.makedirs(output_path + "/images_2", exist_ok=True)
    os.makedirs(output_path + "/images_4", exist_ok=True)
    os.makedirs(output_path + "/images_8", exist_ok=True)
    # Get the list of files in the source directory
    files = os.listdir(images_dir)
    # Copy each file from the source directory to the destination directory
    for file in files:
        source_file = os.path.join(images_dir, file)

        try:
            # 打开原始图像
            img = Image.open(source_file)

            # 获取原始尺寸
            width, height = img.size

            # 调整为50%大小并保存
            new_size = (width // 2, height // 2)
            img_resized = img.resize(new_size, Image.LANCZOS)
            destination_file = os.path.join(output_path, "images_2", file)
            img_resized.save(destination_file, quality=95)

            # 调整为25%大小并保存
            new_size = (width // 4, height // 4)
            img_resized = img.resize(new_size, Image.LANCZOS)
            destination_file = os.path.join(output_path, "images_4", file)
            img_resized.save(destination_file, quality=95)

            # 调整为12.5%大小并保存
            new_size = (width // 8, height // 8)
            img_resized = img.resize(new_size, Image.LANCZOS)
            destination_file = os.path.join(output_path, "images_8", file)
            img_resized.save(destination_file, quality=95)

            # 关闭图像
            img.close()

        except Exception as e:
            logging.error(f"图像调整大小失败: {str(e)}")
            exit(1)

print("Done.")

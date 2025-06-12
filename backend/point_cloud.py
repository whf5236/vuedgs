import os
import subprocess
import json
import shutil
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import time
import threading
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

point_cloud_bp = Blueprint('point_cloud', __name__)

# 存储处理任务的状态
processing_tasks = {}

def run_convert_script(app, source_path, user_id, task_id, output_folder=None):
    """
    运行点云转换脚本的函数

    参数:
        app: Flask 应用实例
        source_path: 源图片文件夹路径
        user_id: 用户ID
        task_id: 任务ID
        output_folder: 输出文件夹路径（可选，不再使用）
    """
    try:
        # 使用应用上下文
        with app.app_context():
            # 获取原始文件夹名称
            folder_name = os.path.basename(source_path)
            logger.info(f"原始文件夹名称: {folder_name}")

            # 创建 colmap 输出文件夹（在原图片路径下，命名为原文件夹名加上 _colmap）
            colmap_folder = f"{source_path}_colmap"
            logger.info(f"COLMAP 输出文件夹: {colmap_folder}")

            # 更新任务状态为处理中
            processing_tasks[task_id] = {
                'status': 'processing',
                'progress': 0,
                'message': 'Starting point cloud processing...',
                'user_id': user_id,
                'source_path': source_path,
                'output_folder': colmap_folder,  # 使用新的 colmap 文件夹
                'start_time': time.time()
            }
            logger.info(f"任务 {task_id} 已创建，用户: {user_id}")

            # 确保输出文件夹存在
            os.makedirs(colmap_folder, exist_ok=True)
            logger.info(f"已创建输出文件夹: {colmap_folder}")

            # 检查源文件夹中的图片
            images_folder = os.path.join(source_path, 'images')
            if os.path.exists(images_folder) and os.path.isdir(images_folder):
                image_files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                logger.info(f"源文件夹中的图片数量: {len(image_files)}")
            else:
                logger.warning(f"源文件夹中没有 images 子文件夹: {images_folder}")

            # 构建命令
            script_path = os.path.join(current_app.root_path, 'gs', 'convert.py')
            command = [
                'python',
                script_path,
                '--source_path', source_path,
                '--output_path', colmap_folder,  # 使用 colmap 文件夹作为输出路径
                '--resize'  # 添加resize参数
            ]

            logger.info(f"处理文件夹: {folder_name}")
            logger.info(f"源路径: {source_path}")
            logger.info(f"COLMAP 输出文件夹: {colmap_folder}")
            logger.info(f"执行命令: {' '.join(command)}")

        # 执行命令
        logger.info(f"Running command: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 保存进程对象，以便可以终止它
        processing_tasks[task_id]['process'] = process

        # 更新进度
        processing_tasks[task_id]['progress'] = 10
        processing_tasks[task_id]['message'] = 'Feature extraction in progress...'

        # 读取输出
        while True:
            # 检查任务是否被取消
            if processing_tasks[task_id]['status'] == 'cancelled':
                logger.info(f"任务已被取消，停止处理: {task_id}")
                break

            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(output.strip())
                # 根据输出更新进度
                if "Running feature extraction" in output:
                    processing_tasks[task_id]['progress'] = 10
                    processing_tasks[task_id]['message'] = 'Feature extraction in progress...'
                elif "Feature extraction failed" in output:
                    processing_tasks[task_id]['status'] = 'failed'
                    processing_tasks[task_id]['message'] = 'Feature extraction failed'
                elif "Running feature matching" in output:
                    processing_tasks[task_id]['progress'] = 30
                    processing_tasks[task_id]['message'] = 'Feature matching in progress...'
                elif "Feature matching failed" in output:
                    processing_tasks[task_id]['status'] = 'failed'
                    processing_tasks[task_id]['message'] = 'Feature matching failed'
                elif "mapper" in output.lower():
                    processing_tasks[task_id]['progress'] = 50
                    processing_tasks[task_id]['message'] = 'Bundle adjustment in progress...'
                elif "Mapper failed" in output:
                    processing_tasks[task_id]['status'] = 'failed'
                    processing_tasks[task_id]['message'] = 'Bundle adjustment failed'
                elif "image_undistorter" in output.lower():
                    processing_tasks[task_id]['progress'] = 70
                    processing_tasks[task_id]['message'] = 'Image undistortion in progress...'
                elif "Copying and resizing" in output:
                    processing_tasks[task_id]['progress'] = 80
                    processing_tasks[task_id]['message'] = 'Copying and resizing images...'
                elif "Done" in output:
                    processing_tasks[task_id]['progress'] = 95
                    processing_tasks[task_id]['message'] = 'Finalizing...'

        # 检查任务是否被取消
        if processing_tasks[task_id]['status'] == 'cancelled':
            # 如果任务被取消，强制终止进程
            try:
                process.terminate()
                logger.info(f"进程已终止: {task_id}")
            except Exception as e:
                logger.error(f"终止进程失败: {str(e)}")
            return

        # 检查进程是否成功完成
        return_code = process.wait()

        if return_code == 0:
            # 处理成功
            processing_tasks[task_id]['status'] = 'completed'
            processing_tasks[task_id]['progress'] = 100
            processing_tasks[task_id]['message'] = 'Point cloud processing completed successfully.'
            processing_tasks[task_id]['end_time'] = time.time()

            # 获取原始文件夹名称和 colmap 文件夹名称
            folder_name = os.path.basename(source_path)
            colmap_folder_name = f"{folder_name}_colmap"
            colmap_folder = processing_tasks[task_id]['output_folder']

            # 不需要复制处理结果，因为现在直接输出到 colmap 文件夹
            logger.info(f"处理结果已直接保存到 {colmap_folder}")

            # 创建结果摘要
            result_summary = {
                'task_id': task_id,
                'user_id': user_id,
                'source_path': source_path,
                'output_folder': colmap_folder,
                'folder_name': folder_name,
                'colmap_folder_name': colmap_folder_name,
                'status': 'completed',
                'processing_time': processing_tasks[task_id]['end_time'] - processing_tasks[task_id]['start_time'],
                'timestamp': time.time()
            }

            # 保存结果摘要到文件
            summary_file = os.path.join(colmap_folder, 'processing_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(result_summary, f, indent=4)

            logger.info(f"保存结果摘要到: {summary_file}")

            logger.info(f"Point cloud processing completed for task {task_id}")
        else:
            # 处理失败
            error_output = process.stderr.read()
            processing_tasks[task_id]['status'] = 'failed'

            # 检查是否是图像尺寸不匹配错误
            if "distorted_camera.width == distorted_bitmap.Width()" in error_output:
                error_message = "图像尺寸与相机参数不匹配。这通常是由于图像在上传或处理过程中被修改了尺寸。请尝试重新上传图像，确保所有图像尺寸一致。"
                processing_tasks[task_id]['message'] = error_message
            else:
                processing_tasks[task_id]['message'] = f'Processing failed with code {return_code}: {error_output}'

            processing_tasks[task_id]['error'] = error_output
            logger.error(f"Point cloud processing failed for task {task_id}: {error_output}")

    except Exception as e:
        # 处理异常
        processing_tasks[task_id]['status'] = 'failed'
        processing_tasks[task_id]['message'] = f'Processing failed with exception: {str(e)}'
        processing_tasks[task_id]['error'] = str(e)
        logger.exception(f"Exception during point cloud processing for task {task_id}")

@point_cloud_bp.route('/process', methods=['POST'])
# 暂时移除 JWT 认证要求
def process_point_cloud():
    """
    处理点云数据的API端点
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username', 'default_user')
    logger.info(f"处理点云请求 - 用户: {user_id}")

    data = request.json
    logger.info(f"请求数据: {data}")

    if not data or 'folder_name' not in data:
        logger.error("缺少文件夹名称")
        return jsonify({'error': 'Folder name is required'}), 400

    folder_name = data['folder_name']
    logger.info(f"处理文件夹: {folder_name}")

    # 构建源路径
    data_folder = os.path.join(current_app.root_path, 'data')
    source_path = os.path.join(data_folder, user_id, folder_name)
    logger.info(f"源路径: {source_path}")

    # 输出文件夹将在 run_convert_script 函数中创建，命名为 source_path + "_colmap"
    output_folder = None  # 不再需要预先定义输出文件夹

    # 检查源文件夹是否存在
    if not os.path.exists(source_path):
        logger.error(f"源文件夹不存在: {source_path}")
        return jsonify({'error': 'Source folder does not exist'}), 404

    if not os.path.isdir(source_path):
        logger.error(f"源路径不是文件夹: {source_path}")
        return jsonify({'error': 'Source path is not a directory'}), 400

    # 检查源文件夹中是否有images子文件夹
    images_folder = os.path.join(source_path, 'images')
    logger.info(f"检查图片文件夹: {images_folder}")

    if not os.path.exists(images_folder):
        logger.error(f"图片文件夹不存在: {images_folder}")
        return jsonify({'error': 'Images folder not found in the source directory'}), 404

    if not os.path.isdir(images_folder):
        logger.error(f"图片路径不是文件夹: {images_folder}")
        return jsonify({'error': 'Images path is not a directory'}), 400

    # 检查图片文件夹中是否有图片
    image_files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    logger.info(f"图片文件夹中的图片数量: {len(image_files)}")

    if len(image_files) == 0:
        logger.error(f"图片文件夹中没有图片: {images_folder}")
        return jsonify({'error': 'No images found in the images folder'}), 400

    # 生成任务ID
    task_id = f"{user_id}_{folder_name}_{int(time.time())}"
    logger.info(f"生成任务ID: {task_id}")

    # 启动处理线程，传递 app 参数
    thread = threading.Thread(
        target=run_convert_script,
        args=(current_app._get_current_object(), source_path, user_id, task_id, output_folder)
    )
    thread.daemon = True
    thread.start()
    logger.info(f"启动处理线程: {task_id}")

    return jsonify({
        'message': 'Point cloud processing started',
        'task_id': task_id,
        'status': 'processing'
    }), 202

@point_cloud_bp.route('/status/<task_id>', methods=['GET'])
# 暂时移除 JWT 认证要求
def get_task_status(task_id):
    """
    获取任务状态的API端点
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username', 'default_user')

    if task_id not in processing_tasks:
        return jsonify({'error': 'Task not found'}), 404

    # 检查任务是否属于当前用户
    if processing_tasks[task_id]['user_id'] != user_id:
        return jsonify({'error': 'Unauthorized access to task'}), 403

    # 返回任务状态
    task_info = {
        'task_id': task_id,
        'status': processing_tasks[task_id]['status'],
        'progress': processing_tasks[task_id]['progress'],
        'message': processing_tasks[task_id]['message']
    }

    # 如果任务已完成，添加结果信息
    if processing_tasks[task_id]['status'] == 'completed':
        task_info['output_folder'] = processing_tasks[task_id]['output_folder']
        task_info['processing_time'] = processing_tasks[task_id]['end_time'] - processing_tasks[task_id]['start_time']

    # 如果任务失败，添加错误信息
    if processing_tasks[task_id]['status'] == 'failed' and 'error' in processing_tasks[task_id]:
        task_info['error'] = processing_tasks[task_id]['error']

    return jsonify(task_info), 200

@point_cloud_bp.route('/folders', methods=['GET'])
# 暂时移除 JWT 认证要求
def get_folders():
    """
    获取用户可用于点云处理的文件夹列表
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username', 'default_user')

    # 构建用户数据文件夹路径
    user_data_folder = os.path.join(current_app.root_path, 'data', user_id)

    # 检查用户数据文件夹是否存在
    if not os.path.exists(user_data_folder) or not os.path.isdir(user_data_folder):
        return jsonify({'folders': []}), 200

    # 获取所有子文件夹
    folders = []
    for item in os.listdir(user_data_folder):
        item_path = os.path.join(user_data_folder, item)
        # 检查是否是文件夹且包含images子文件夹
        if os.path.isdir(item_path) and item != 'point_cloud_results':
            images_folder = os.path.join(item_path, 'images')
            if os.path.exists(images_folder) and os.path.isdir(images_folder):
                # 获取文件夹信息
                folder_info = {
                    'name': item,
                    'path': item_path,
                    'image_count': len([f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]),
                    'created_time': os.path.getctime(item_path)
                }
                folders.append(folder_info)

    # 按创建时间降序排序
    folders.sort(key=lambda x: x['created_time'], reverse=True)

    return jsonify({'folders': folders}), 200

@point_cloud_bp.route('/cancel/<task_id>', methods=['POST'])
# 暂时移除 JWT 认证要求
def cancel_task(task_id):
    """
    取消正在进行的点云处理任务
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username', 'default_user')
    logger.info(f"取消任务请求 - 用户: {user_id}, 任务ID: {task_id}")

    if task_id not in processing_tasks:
        logger.error(f"任务不存在: {task_id}")
        return jsonify({'error': 'Task not found'}), 404

    # 检查任务是否属于当前用户
    if processing_tasks[task_id]['user_id'] != user_id:
        logger.error(f"未授权访问任务: {task_id}")
        return jsonify({'error': 'Unauthorized access to task'}), 403

    # 检查任务是否已经完成或失败
    if processing_tasks[task_id]['status'] in ['completed', 'failed', 'cancelled']:
        logger.warning(f"任务已经 {processing_tasks[task_id]['status']}: {task_id}")
        return jsonify({'message': f"Task already {processing_tasks[task_id]['status']}"}), 200

    # 更新任务状态为取消
    processing_tasks[task_id]['status'] = 'cancelled'
    processing_tasks[task_id]['message'] = 'Task cancelled by user'
    processing_tasks[task_id]['end_time'] = time.time()
    logger.info(f"任务已取消: {task_id}")

    # 尝试终止进程
    if 'process' in processing_tasks[task_id]:
        try:
            process = processing_tasks[task_id]['process']
            process.terminate()
            logger.info(f"进程已终止: {task_id}")
        except Exception as e:
            logger.error(f"终止进程失败: {str(e)}")

    return jsonify({'message': 'Task cancelled successfully'}), 200

@point_cloud_bp.route('/results', methods=['GET'])
def get_point_cloud_results():
    """
    Scans for and returns a list of processed COLMAP folders for a given user.
    This version has relaxed filtering to ensure all potential training folders are listed.
    """
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400

    try:
        user_data_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], username)
        logger.info(f"Scanning for results in: {user_data_folder}")

        if not os.path.exists(user_data_folder) or not os.path.isdir(user_data_folder):
            logger.warning(f"User data folder not found for user '{username}' at '{user_data_folder}'")
            return jsonify({'results': []})

        results = []
        for folder_name in os.listdir(user_data_folder):
            folder_path = os.path.join(user_data_folder, folder_name)
            if os.path.isdir(folder_path):
                # Basic check: Add any folder that seems to be a COLMAP output.
                # A more robust check could look for 'sparse' or 'images' subdirectories.
                # For now, we list any folder ending with '_colmap' or containing 'colmap'.
                if 'colmap' in folder_name.lower():
                    try:
                        creation_time = os.path.getctime(folder_path)
                        result_item = {
                            'folder_name': folder_name,
                            'name': folder_name,
                            'timestamp': creation_time,
                            'created_time': creation_time, # For compatibility
                            'output_folder': folder_path,
                            'status': 'completed' # Assume completion
                        }
                        results.append(result_item)
                    except Exception as e:
                        logger.error(f"Could not process folder {folder_path}: {e}")

        logger.info(f"Found {len(results)} processed folders for user '{username}'.")
        # Sort results by timestamp descending
        results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        return jsonify({'results': results})

    except Exception as e:
        logger.error(f"Error fetching point cloud results for user '{username}': {str(e)}", exc_info=True)
        return jsonify({'error': 'An internal error occurred while fetching results.'}), 500

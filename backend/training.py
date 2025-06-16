import os
import subprocess
import json
import time
import threading
import logging
import numpy as np
from flask import Blueprint, request, jsonify, current_app
import sys

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('training')

# 创建蓝图
training_bp = Blueprint('training', __name__)

# 存储训练任务的状态
training_tasks = {}


# New wrapper function
def run_training_script_wrapper(root_path, source_path, model_path, user_id, task_id, params=None):
    _internal_run_training_script(root_path, source_path, model_path, user_id, task_id, params)

def _internal_run_training_script(root_path, source_path, model_path, user_id, task_id, params=None):
    # 首先创建任务记录，确保在异常处理中可以访问
    training_tasks[task_id] = {
        'status': 'initializing',
        'progress': 0,
        'message': 'Initializing training (from internal)...',
        'user_id': user_id,
        'source_path': source_path,
        'model_path': model_path,
        'start_time': time.time(),
    }

    try:
        # Application context is now set by the wrapper
        # 获取原始文件夹名称
        folder_name = os.path.basename(source_path)

        # 确保模型输出目录存在
        os.makedirs(model_path, exist_ok=True)

        # 更新任务状态为处理中
        training_tasks[task_id]['status'] = '处理中'
        training_tasks[task_id]['message'] = '开始训练'

        # 构建命令
        script_path = os.path.join(root_path, 'backend', 'gs', 'train.py')
        command = [
            sys.executable,
            script_path,
            '--source_path', source_path,
            '--model_path', model_path
        ]

        # 确保WebSocket参数正确传递
        websocket_host = 'localhost'
        websocket_port = 6009
        
        if params:
    
            # 确保WebSocket参数被正确添加到命令行
            command.extend(['--ip', str(websocket_host)])
            command.extend(['--port', str(websocket_port)])
            
            
            # 添加其他参数
            for key, value in params.items():
                if key in ['ip', 'port']:
                    continue
                    
                if value is not None:
                    # 处理布尔标志 - 布尔标志只有在为 True 时才添加，为 False 时完全忽略
                    if isinstance(value, bool):
                        if value:  # 只有当布尔值为 True 时才添加标志
                            command.append(f'--{key}')
                        # 如果是 False，不添加任何参数
                    # 处理列表参数（如 test_iterations）
                    elif isinstance(value, list):
                        if value:  # 只有当列表非空时才添加参数
                            command.append(f'--{key}')
                            command.extend([str(item) for item in value])
                    # 处理其他参数，但要特别处理字符串 "True" 和 "False"
                    elif value != "":
                        # 检查是否是字符串形式的布尔值
                        if str(value).lower() == "true":
                            command.append(f'--{key}')
                        elif str(value).lower() == "false":
                            # 如果是 "false"，不添加任何参数
                            pass
                        else:
                            command.append(f'--{key}')
                            command.append(str(value))

        # 执行命令
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
            universal_newlines=True  # 确保文本模式
        )

        # 保存进程对象，以便可以终止它
        training_tasks[task_id]['process'] = process
        
        # 保存WebSocket配置
        training_tasks[task_id]['websocket'] = {
            'host': websocket_host,
            'port': websocket_port
        }

        # 更新进度
        training_tasks[task_id]['progress'] = 5
        training_tasks[task_id]['message'] = '训练开始...'

        from threading import Thread

        def read_output(pipe, is_error=False):
            prefix = "ERROR: " if is_error else ""
            for line in iter(pipe.readline, ''):
                if not line:
                    break
                line = line.strip()
                if line:
                    # 记录到日志
                    log_prefix = "STDERR: " if is_error else "STDOUT: "
                    logger.info(f"{log_prefix}{line}")

                    # 解析输出，更新进度
                    if not is_error and "Iteration" in line:
                        try:
                            # 尝试从输出中提取当前迭代次数
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == "Iteration":
                                    current_iteration = int(parts[i+1].strip(','))
                                    total_iterations = params.get('iterations', 30000) if params else 30000
                                    progress = min(95, int(current_iteration / total_iterations * 100))
                                    training_tasks[task_id]['progress'] = progress
                                    training_tasks[task_id]['message'] = f'Training in progress... Iteration {current_iteration}/{total_iterations}'
                        except Exception as e:
                            logger.error(f"解析输出失败: {str(e)}")

                    # 检查是否保存了模型
                    if not is_error and "Saving Gaussians" in line:
                        training_tasks[task_id]['message'] = 'Saving model checkpoint...'


        # 启动读取线程
        stdout_thread = Thread(target=read_output, args=(process.stdout,))
        stderr_thread = Thread(target=read_output, args=(process.stderr, True))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        # 等待进程完成
        process.wait()

        # 等待读取线程完成
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)

        # 检查任务是否被取消
        if training_tasks[task_id]['status'] == 'cancelled':
            try:
                process.terminate()
                logger.info(f"进程已终止: {task_id}")
            except Exception as e:
                logger.error(f"终止进程失败: {str(e)}")
            return

        # 检查进程是否成功完成
        return_code = process.returncode

        if return_code == 0:
            # 训练成功
            training_tasks[task_id]['status'] = 'completed'
            training_tasks[task_id]['progress'] = 100
            training_tasks[task_id]['message'] = 'Training completed successfully.'
            training_tasks[task_id]['end_time'] = time.time()
            
            # 注意：WebSocket广播完成消息代码已移除

            # 创建结果摘要
            result_summary = {
                'task_id': task_id,
                'user_id': user_id,
                'source_path': source_path,
                'model_path': model_path,
                'folder_name': folder_name,
                'status': 'completed',
                'processing_time': training_tasks[task_id]['end_time'] - training_tasks[task_id]['start_time'],
                'timestamp': time.time()
            }

            # 保存结果摘要到文件
            summary_file = os.path.join(model_path, 'training_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(result_summary, f, indent=4)

            logger.info(f"保存结果摘要到: {summary_file}")
            logger.info(f"训练完成: {task_id}")
        else:
            # 训练失败
            training_tasks[task_id]['status'] = 'failed'
            training_tasks[task_id]['message'] = f'Training failed with code {return_code}'
            
            error_message = f"训练进程异常退出，返回码: {return_code}"  # 添加详细的错误信息
            training_tasks[task_id]['error'] = error_message

            logger.error(f"训练失败: {task_id}, 返回码: {return_code}")

    except Exception as e:
        # 处理异常
        training_tasks[task_id]['status'] = 'failed'
        error_message = f'Training failed with exception: {str(e)}'
        training_tasks[task_id]['message'] = error_message
        training_tasks[task_id]['error'] = str(e)

        # 添加到输出日志
        if 'output_logs' in training_tasks[task_id]:
            training_tasks[task_id]['output_logs'].append(f"CRITICAL ERROR: {error_message}")
        else:
            training_tasks[task_id]['output_logs'] = [f"CRITICAL ERROR: {error_message}"]

        # 记录详细的异常信息
        logger.exception(f"训练过程中发生异常: {task_id}")

        # 设置结束时间
        training_tasks[task_id]['end_time'] = time.time()

def generate_model_path(root_path, user_id, source_folder):
    """
    生成模型输出路径：源文件夹名_model，如果存在则添加序号
    
    Args:
        root_path: 应用根路径
        user_id: 用户ID
        source_folder: 源文件夹名称
    
    Returns:
        str: 生成的模型路径
    """
    base_name = f"{source_folder}_model"
    base_path = os.path.join(root_path, 'data', user_id, 'models', base_name)
    
    # 如果基础路径不存在，直接返回
    if not os.path.exists(base_path):
        return base_path
        
    # 如果存在，则添加序号
    counter = 1
    while True:
        new_path = f"{base_path}_{counter}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

@training_bp.route('/start', methods=['POST'])
def start_training():
    data = request.json
    logger.info(f"收到开始训练请求: {data}")

    if not data:
        logger.error("请求中没有提供JSON数据")
        return jsonify({'error': 'No data provided'}), 400

    # 兼容 userId 和 username
    user_id = data.get('userId') or data.get('username')
    
    # 兼容 folderPath (文件夹名) 和 source_path (完整路径)
    folder_path_or_name = data.get('folderPath') or data.get('source_path')
    
    params = data.get('params', {})

    if not user_id or not folder_path_or_name:
        logger.error(f"请求中缺少用户标识或路径。收到 user_id: {user_id}, folder_path: {folder_path_or_name}")
        return jsonify({'error': 'userId/username and folderPath/source_path are required'}), 400

    # 如果传入的是完整路径，则提取最后的文件夹名
    if os.path.isabs(folder_path_or_name):
        folder_name = os.path.basename(folder_path_or_name)
    else:
        folder_name = folder_path_or_name

    # 获取Flask应用的根目录 (...\login_project\backend)
    backend_path = current_app.root_path
    # 从中推断出项目的工作区根目录 (...\login_project), 用于寻找 gs/train.py
    project_root = os.path.dirname(backend_path)

    # 构建数据源的绝对路径 (在 backend/data 目录下)
    source_path = os.path.join(backend_path, 'data', user_id, folder_name)
    logger.info(f"构建的数据源路径: {source_path}")
    
    # 检查数据源目录是否存在
    if not os.path.isdir(source_path):
        logger.error(f"数据源路径不存在: {source_path}")
        # 注意：这里的路径是服务器上的绝对路径，在返回给前端时请注意信息安全
        return jsonify({'error': f'Source path does not exist on server'}), 400

    # 生成模型输出路径 (在 backend/data 目录下)
    model_path = generate_model_path(backend_path, user_id, folder_name)
    logger.info(f"生成的模型输出路径: {model_path}")

    # 合并和准备训练参数
    training_params = {
        'sh_degree': 3,
        'iterations': 7000,
        'test_iterations': [7000, 30000],
        'save_iterations': [7000, 30000],
        'eval': False,
        'quiet': False
    }
    training_params.update(params or {})

    websocket_host = training_params.get('ip', '127.0.0.1')
    websocket_port = training_params.get('port', 6009)
    training_params['ip'] = websocket_host
    training_params['port'] = websocket_port
    
    # 生成任务ID
    task_id = f"{user_id}_{folder_name}_{int(time.time())}"
    logger.info(f"生成的任务ID: {task_id}")

    # 检查此任务是否已在运行
    for tid, task_info in training_tasks.items():
        if task_info.get('source_path') == source_path and task_info.get('status') in ['running', 'initializing', '处理中']:
            return jsonify({'error': f'任务已在运行: {tid}'}), 400

    # 启动训练线程
    # 传递 project_root 以便脚本能找到 gs/train.py
    thread = threading.Thread(
        target=_internal_run_training_script,
        args=(project_root, source_path, model_path, user_id, task_id, training_params)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Training started',
        'task_id': task_id,
        'websocket': {
            'host': websocket_host,
            'port': websocket_port
        }
    }), 200

@training_bp.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取训练任务状态的API端点
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username')
    if task_id not in training_tasks:
        return jsonify({'error': 'Task not found'}), 404

    # 检查任务是否属于当前用户
    if training_tasks[task_id]['user_id'] != user_id:
        return jsonify({'error': 'Unauthorized access to task'}), 403

    # 返回任务状态
    task_info = {
        'task_id': task_id,
        'status': training_tasks[task_id]['status'],
        'progress': training_tasks[task_id]['progress'],
        'message': training_tasks[task_id]['message']
    }


    # 如果任务已完成，添加结果信息
    if training_tasks[task_id]['status'] == 'completed':
        task_info['model_path'] = training_tasks[task_id]['model_path']
        task_info['processing_time'] = training_tasks[task_id]['end_time'] - training_tasks[task_id]['start_time']

    # 如果任务失败，添加错误信息
    if training_tasks[task_id]['status'] == 'failed' and 'error' in training_tasks[task_id]:
        task_info['error'] = training_tasks[task_id]['error']

    return jsonify(task_info), 200


@training_bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """
    取消训练任务的API端点
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username', 'default_user')
    
    # 调用共享的取消逻辑
    result = cancel_training_task(user_id, task_id)
    
    # 处理返回结果
    if 'error' in result:
        if result['error'] == 'Unauthorized access to task':
            return jsonify(result), 403
    
    return jsonify(result), 200

def cancel_training_task(username, task_id):
    """
    取消训练任务的函数（供WebSocket和HTTP调用）
    """
    logger.info(f"取消训练请求 - 用户: {username}, 任务ID: {task_id}")

    if task_id not in training_tasks:
        logger.warning(f"任务不存在，可能已被清理: {task_id}")
        # 任务不存在时返回成功状态，让前端能正常重置
        return {'message': 'Task not found or already cleaned up, treating as cancelled'}
    
    # 从任务ID中提取所有者ID进行验证
    try:
        owner_id = task_id.split('_')[0]
    except IndexError:
        logger.error(f"无法从任务ID中解析所有者ID: {task_id}")
        return {'error': 'Invalid task ID format'}

    # 检查任务是否属于当前用户
    if owner_id != username:
        logger.error(f"未授权访问任务: {task_id}. 请求者: {username}, 所有者: {owner_id}")
        return {'error': 'Unauthorized access to task'}

    # 检查任务是否已经完成或失败
    if training_tasks[task_id]['status'] in ['completed', 'failed', 'cancelled']:
        logger.warning(f"任务已经 {training_tasks[task_id]['status']}: {task_id}")
        return {'message': f"Task already {training_tasks[task_id]['status']}"}

    # 更新任务状态为取消
    training_tasks[task_id]['status'] = 'cancelled'
    training_tasks[task_id]['message'] = 'Task cancelled by user'
    training_tasks[task_id]['end_time'] = time.time()
    logger.info(f"任务已取消: {task_id}")
    
    # 注意：WebSocket广播取消消息代码已移除

    # 尝试终止进程
    if 'process' in training_tasks[task_id]:
        try:
            process = training_tasks[task_id]['process']
            process.terminate()
            logger.info(f"进程已终止: {task_id}")
        except Exception as e:
            logger.error(f"终止进程失败: {str(e)}")

    return {'message': 'Task cancelled successfully'}

@training_bp.route('/active', methods=['GET'])
def get_active_tasks():
    """
    获取用户的活动训练任务，并清理所有已结束的任务。
    """
    user_id = request.args.get('username')
    
    if not user_id:
        return jsonify({'error': 'Username is required'}), 400

    active_tasks = []
    tasks_to_remove = []

    # 使用 list(training_tasks.items()) 避免在迭代时修改字典
    for task_id, task_info in list(training_tasks.items()):
        if isinstance(task_info, dict) and task_info.get('user_id') == user_id:
            status = task_info.get('status')
            
            if status in ['处理中', 'initializing']:
                active_tasks.append({
                    'task_id': task_id,
                    'status': task_info.get('status'),
                    'progress': task_info.get('progress'),
                    'message': task_info.get('message'),
                    'start_time': task_info.get('start_time')
                })
            elif status in ['completed', 'failed', 'cancelled']:
                tasks_to_remove.append(task_id)

    # 集中清理所有已完成、失败或取消的任务
    for task_id in tasks_to_remove:
        if task_id in training_tasks:
            try:
                del training_tasks[task_id]
                logger.info(f"已从内存中清理已结束的任务: {task_id}")
            except KeyError:
                logger.warning(f"尝试清理一个不存在的任务，可能已被其他进程处理: {task_id}")
    
    return jsonify({'active_tasks': active_tasks}), 200

@training_bp.route('/cleanup', methods=['POST'])
def cleanup_completed_tasks():
    """
    此函数的功能已合并到 get_active_tasks 中，保留以实现向后兼容。
    """
    return jsonify({'cleaned_tasks': 0, 'message': 'Cleanup is now handled by get_active_tasks.'}), 200

@training_bp.route('/results', methods=['GET'])
def get_results():

    # 使用请求参数中的用户名
    user_id = request.args.get('username')
    # 构建用户模型文件夹路径
    if user_id is None:
        return jsonify({'error': '未提供用户名'}), 400
        
    user_models_folder = os.path.join(current_app.root_path, 'data', user_id, 'models')

    # 检查用户模型文件夹是否存在
    if not os.path.exists(user_models_folder) or not os.path.isdir(user_models_folder):
        return jsonify({'results': []}), 200

    # 获取所有模型文件夹
    results = []
    for item in os.listdir(user_models_folder):
        item_path = os.path.join(user_models_folder, item)
        if os.path.isdir(item_path):
            # 检查是否有训练摘要文件
            summary_file = os.path.join(item_path, 'training_summary.json')
            if os.path.exists(summary_file):
                try:
                    with open(summary_file, 'r') as f:
                        summary = json.load(f)
                        results.append(summary)
                except Exception as e:
                    logger.error(f"读取摘要文件失败 {summary_file}: {str(e)}")
            else:
                # 如果没有摘要文件，创建基本信息
                results.append({
                    'folder_name': item,
                    'model_path': item_path,
                    'created_time': os.path.getctime(item_path),
                    'status': '未知'
                })
    results.sort(key=lambda x: x.get('timestamp', 0) if isinstance(x, dict) and 'timestamp' in x else 0, reverse=True)
    return jsonify({'results': results}), 200

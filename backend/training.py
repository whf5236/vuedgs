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
        script_path = os.path.join(root_path, 'gs', 'train.py')
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
        training_tasks[task_id]['message'] = 'Training started...'

        # 添加启动信息到日志
        start_message = f"Starting training process with command: {' '.join(command)}"
        training_tasks[task_id]['output_logs'].append(start_message)
        logger.info(start_message)
        
        # 使用简单的方式读取输出
        from threading import Thread

        # 定义读取输出的函数
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

                    # 添加到任务日志
                    training_tasks[task_id]['output_logs'].append(f"{prefix}{line}")
                    # 限制日志列表大小
                    if len(training_tasks[task_id]['output_logs']) > 1000:
                        training_tasks[task_id]['output_logs'] = training_tasks[task_id]['output_logs'][-1000:]

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

                    # 检查是否计算了测试集指标
                    if not is_error and "Test set results" in line:
                        # 尝试提取 PSNR 值
                        try:
                            if "PSNR" in line:
                                psnr_parts = line.split("PSNR")
                                psnr_value = float(psnr_parts[1].split()[0])
                                training_tasks[task_id]['psnr'] = psnr_value
                                training_tasks[task_id]['message'] = f'PSNR: {psnr_value:.2f}'
                        except Exception as e:
                            logger.error(f"提取 PSNR 失败: {str(e)}")

                    # 检查高斯点数量
                    if not is_error and "Number of points" in line:
                        try:
                            parts = line.split(":")
                            if len(parts) > 1:
                                num_gaussians = int(parts[1].strip().split()[0])
                                training_tasks[task_id]['num_gaussians'] = num_gaussians
                        except Exception as e:
                            logger.error(f"提取高斯点数量失败: {str(e)}")

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
        end_message = f"Training process ended with return code: {return_code}"
        training_tasks[task_id]['output_logs'].append(end_message)
        logger.info(end_message)

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

            # 如果有 PSNR 值，添加到结果中
            if 'psnr' in training_tasks[task_id]:
                result_summary['psnr'] = training_tasks[task_id]['psnr']

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
            training_tasks[task_id]['output_logs'].append(f"ERROR: {error_message}")

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
    if not data or 'source_path' not in data:
        return jsonify({'error': '需要源文件夹'}), 400
    
    # 从请求体中获取用户名
    user_id = data.get('username')
    source_path = data['source_path']

    # 检查源路径是否存在
    if not os.path.exists(source_path):
        return jsonify({'error': '源路径不存在'}), 404

    if not os.path.isdir(source_path):
        return jsonify({'error': '源路径不是文件夹'}), 400

    # 获取源文件夹名称并生成模型路径
    source_folder = os.path.basename(source_path)
    model_path = generate_model_path(current_app.root_path, user_id, source_folder)
    
    # 确保模型输出目录存在
    os.makedirs(model_path, exist_ok=True)

    # 获取训练参数
    training_params = data.get('params', {})
    websocket_port = data.get('websocket_port', 6009)  # 从请求中获取端口，默认6009
    websocket_host = data.get('websocket_host', 'localhost')  # 从请求中获取主机，默认localhost

    training_params['ip'] = websocket_host
    training_params['port'] = websocket_port
    # 生成任务ID
    task_id = f"{user_id}_{folder_name}_{int(time.time())}"
    logger.info(f"生成任务ID: {task_id}")

    # 启动训练线程
    # 传递应用根目录，而不是整个app对象
    root_path = current_app.root_path
    thread = threading.Thread(
        target=run_training_script_wrapper,
        args=(root_path, source_path, model_path, user_id, task_id, training_params)
    )
    thread.daemon = True
    thread.start()
    return jsonify({
        'message': 'Training started',
        'task_id': task_id,
        'status': 'processing',
        'model_path': model_path,
        'visualization': {
            'host': websocket_host,
            'port': websocket_port
        },
        'websocket': {
            'host': websocket_host,
            'port': websocket_port,
            'url': f'ws://{websocket_host}:{websocket_port}'
        }
    }), 202

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

    # 添加输出日志
    if 'output_logs' in training_tasks[task_id]:
        task_info['output_logs'] = training_tasks[task_id]['output_logs'][-100:]

    # 如果任务已完成，添加结果信息
    if training_tasks[task_id]['status'] == 'completed':
        task_info['model_path'] = training_tasks[task_id]['model_path']
        task_info['processing_time'] = training_tasks[task_id]['end_time'] - training_tasks[task_id]['start_time']
        if 'psnr' in training_tasks[task_id]:
            task_info['psnr'] = training_tasks[task_id]['psnr']

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
    获取用户的活动训练任务
    """
    user_id = request.args.get('username')
    
    # 获取用户的活动任务（只包含真正在处理中的任务）
    active_tasks = []
    for task_id, task_info in training_tasks.items():
        if task_info['user_id'] == user_id and task_info['status'] in ['processing', 'initializing']:
            active_tasks.append({
                'task_id': task_id,
                'status': task_info['status'],
                'progress': task_info['progress'],
                'message': task_info['message'],
                'start_time': task_info['start_time']
            })
    
    # 清理已取消的任务（立即清理，不等待5分钟）
    cancelled_tasks_to_remove = []
    for task_id, task_info in training_tasks.items():
        if (task_info['user_id'] == user_id and 
            task_info['status'] == 'cancelled'):
            cancelled_tasks_to_remove.append(task_id)
    
    for task_id in cancelled_tasks_to_remove:
        del training_tasks[task_id]
        logger.info(f"已清理取消的任务: {task_id}")
    
    return jsonify({'active_tasks': active_tasks}), 200

@training_bp.route('/cleanup', methods=['POST'])
def cleanup_completed_tasks():
    """
    清理已完成的训练任务
    """
    user_id = request.args.get('username')
    
    # 清理已完成、失败或取消的任务
    tasks_to_remove = []
    for task_id, task_info in training_tasks.items():
        if (task_info['user_id'] == user_id and 
            task_info['status'] in ['completed', 'failed', 'cancelled'] and
            'end_time' in task_info and
            time.time() - task_info['end_time'] > 300):  # 5分钟后清理
            tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del training_tasks[task_id]
        logger.info(f"已清理任务: {task_id}")
    
    return jsonify({'cleaned_tasks': len(tasks_to_remove)}), 200

@training_bp.route('/results', methods=['GET'])
def get_results():
    """
    获取用户的训练结果列表
    """
    # 使用请求参数中的用户名
    user_id = request.args.get('username')

    # 构建用户模型文件夹路径
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
                    'status': 'unknown'
                })

    # 按时间戳降序排序
    results.sort(key=lambda x: x.get('timestamp', 0) if isinstance(x, dict) and 'timestamp' in x else 0, reverse=True)

    return jsonify({'results': results}), 200

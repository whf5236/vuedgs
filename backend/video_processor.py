import os
import cv2
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_frames_from_video(video_path, output_folder, frame_rate=1, extract_all=False):
    try:
        # 确保输出文件夹存在
        os.makedirs(output_folder, exist_ok=True)

        # 获取images子文件夹
        images_folder = os.path.join(output_folder, 'images')
        if not os.path.exists(images_folder):
            os.makedirs(images_folder, exist_ok=True)

        # 打开视频文件
        video = cv2.VideoCapture(video_path)

        # 检查视频是否成功打开
        if not video.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return 0

        # 获取视频属性
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        logger.info(f"视频信息: FPS={fps}, 总帧数={total_frames}, 时长={duration}秒")

        # 计算帧间隔
        if extract_all:
            frame_interval = 1  # 提取每一帧
        else:
            frame_interval = int(fps / frame_rate) if fps > 0 else 1
            frame_interval = max(1, frame_interval)  # 确保至少为1

        logger.info(f"帧间隔: {frame_interval}")

        # 提取帧
        frame_count = 0
        saved_count = 0

        while True:
            ret, frame = video.read()

            if not ret:
                break

            # 根据间隔保存帧
            if frame_count % frame_interval == 0:
                frame_filename = os.path.join(images_folder, f"frame_{saved_count:06d}.jpg")
                cv2.imwrite(frame_filename, frame)
                saved_count += 1

            frame_count += 1

            # 每100帧输出一次日志
            if frame_count % 100 == 0:
                logger.info(f"已处理 {frame_count}/{total_frames} 帧, 已保存 {saved_count} 帧")

        # 释放视频对象
        video.release()

        logger.info(f"帧提取完成. 总共处理了 {frame_count} 帧, 保存了 {saved_count} 帧")
        return saved_count

    except Exception as e:
        logger.exception(f"提取帧时发生错误: {str(e)}")
        return 0

def handle_video_upload(file, username, extract_frames=False, frame_rate=1, extract_all_frames=False, custom_folder_name=None):
    """
    处理视频上传并提取帧

    参数:
    - file: 上传的文件对象
    - username: 用户名
    - extract_frames: 是否提取帧
    - frame_rate: 每秒提取的帧数
    - extract_all_frames: 是否提取所有帧

    返回:
    - 处理结果
    """
    try:
        # 检查文件是否为视频
        if not file.filename or not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.webm', '.mkv')):
            return {
                'success': False,
                'message': 'Invalid video file. Supported formats: MP4, AVI, MOV, WEBM, MKV'
            }

        # 生成安全的文件名
        filename = secure_filename(file.filename)

        # 创建唯一的文件夹名称
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # 如果提供了自定义名称，使用它作为前缀
        if custom_folder_name and custom_folder_name.strip():
            # 移除不安全的字符
            safe_custom_name = ''.join(c for c in custom_folder_name if c.isalnum() or c in '_- ')
            safe_custom_name = safe_custom_name.strip().replace(' ', '_')
            if safe_custom_name:  # 确保清理后的名称不为空
                folder_name = f"{safe_custom_name}_{timestamp}"
            else:
                folder_name = f"{timestamp}_video"
        else:
            folder_name = f"{timestamp}_video"

        # 获取用户文件目录
        user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], username)
        os.makedirs(user_folder, exist_ok=True)

        # 构建视频文件夹路径
        video_folder = os.path.join(user_folder, folder_name)
        os.makedirs(video_folder, exist_ok=True)

        # 创建images子文件夹
        images_folder = os.path.join(video_folder, 'images')
        os.makedirs(images_folder, exist_ok=True)

        # 保存视频文件
        video_path = os.path.join(video_folder, filename)
        file.save(video_path)

        logger.info(f"视频已保存到: {video_path}")

        # 如果是视频文件，也保存一份到images文件夹中
        if filename.lower().endswith(('.mp4', '.avi', '.mov', '.webm', '.mkv')):
            video_in_images = os.path.join(images_folder, filename)
            try:
                # 复制文件到images文件夹
                with open(video_path, 'rb') as src_file:
                    with open(video_in_images, 'wb') as dst_file:
                        dst_file.write(src_file.read())
                logger.info(f"视频已复制到images文件夹: {video_in_images}")
            except Exception as e:
                logger.error(f"复制视频到images文件夹时出错: {str(e)}")

        # 提取帧
        frames_count = 0
        if extract_frames:
            try:
                frame_rate_value = int(frame_rate)
            except (ValueError, TypeError):
                frame_rate_value = 1

            frames_count = extract_frames_from_video(
                video_path,
                video_folder,
                frame_rate=frame_rate_value,
                extract_all=extract_all_frames
            )

            if frames_count > 0:
                logger.info(f"成功从视频中提取了 {frames_count} 帧")
            else:
                logger.warning("未能从视频中提取帧")

        # 返回结果
        return {
            'success': True,
            'message': f'Video uploaded successfully. Extracted {frames_count} frames.' if extract_frames else 'Video uploaded successfully.',
            'filename': filename,
            'folderName': folder_name,
            'path': f'/api/files/{username}/{folder_name}/{filename}',
            'frames_count': frames_count
        }

    except Exception as e:
        logger.exception(f"处理视频上传时发生错误: {str(e)}")
        return {
            'success': False,
            'message': f'Error processing video: {str(e)}'
        }

import os
import zipfile
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import jsonify, current_app, send_from_directory

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'zip'}

def allowed_file(filename):
    """检查文件扩展名是否允许上传"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_directory(username):
    """获取用户文件目录，如果不存在则创建"""
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def create_unique_folder(username, prefix="upload", custom_name=None):
    """创建唯一的文件夹名称并返回完整路径"""
    print(f"创建唯一文件夹 - 用户: {username}, 前缀: {prefix}, 自定义名称: {custom_name}")

    # 生成更友好的时间戳格式
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"生成的时间戳: {timestamp}")

    # 如果提供了自定义名称，直接使用它
    if custom_name:
        # 移除不安全的字符
        safe_custom_name = ''.join(c for c in custom_name if c.isalnum() or c in '_- ')
        safe_custom_name = safe_custom_name.strip().replace(' ', '_')
        print(f"清理后的自定义名称: {safe_custom_name}")

        if safe_custom_name:  # 确保清理后的名称不为空
            folder_name = safe_custom_name

            # 检查文件夹是否已存在，如果存在则添加时间戳以确保唯一性
            user_dir = get_user_directory(username)
            potential_folder_path = os.path.join(user_dir, folder_name)
            if os.path.exists(potential_folder_path):
                print(f"文件夹 {folder_name} 已存在，添加时间戳以确保唯一性")
                folder_name = f"{safe_custom_name}_{timestamp}"
        else:
            folder_name = f"{timestamp}_{prefix}"
    else:
        # 如果没有自定义名称，使用时间戳作为主要标识
        folder_name = f"{timestamp}_{prefix}"

    print(f"最终文件夹名称: {folder_name}")

    # 获取用户目录
    user_dir = get_user_directory(username)
    print(f"用户目录: {user_dir}")

    # 创建新文件夹
    folder_path = os.path.join(user_dir, folder_name)
    print(f"创建文件夹: {folder_path}")
    os.makedirs(folder_path, exist_ok=True)

    # 创建images子文件夹
    images_folder = os.path.join(folder_path, 'images')
    print(f"创建images子文件夹: {images_folder}")
    os.makedirs(images_folder, exist_ok=True)

    return folder_path, folder_name

def handle_single_file_upload(file, username):
    """处理单个文件上传"""
    if not file or file.filename == '':
        return jsonify({'message': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not allowed'}), 400

    # 生成安全的文件名
    filename = secure_filename(file.filename)

    # 创建唯一文件夹
    file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
    folder_path, folder_name = create_unique_folder(username, f"file")

    # 如果是图片文件，直接保存到images子文件夹
    if file_type in ['png', 'jpg', 'jpeg', 'gif']:
        images_folder = os.path.join(folder_path, 'images')
        image_path = os.path.join(images_folder, filename)
        file.save(image_path)
    else:
        # 非图片文件保存到主文件夹
        file_path = os.path.join(folder_path, filename)
        file.save(file_path)

    # 如果是zip文件，解压缩
    if filename.endswith('.zip'):
        extract_dir = os.path.join(folder_path, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

            # 检查解压后的文件中是否有图片，如果有则复制到images文件夹
            for root, _, files in os.walk(extract_dir):
                for extracted_file in files:
                    if extracted_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        extracted_path = os.path.join(root, extracted_file)
                        image_path = os.path.join(images_folder, extracted_file)
                        # 移动图片文件到images文件夹（而不是复制）
                        import shutil
                        shutil.move(extracted_path, image_path)

        return jsonify({
            'message': 'File uploaded and extracted successfully',
            'filename': filename,
            'folderName': folder_name,
            'path': f'/api/files/{username}/{folder_name}/{filename}'
        }), 201

    return jsonify({
        'message': 'File uploaded successfully',
        'filename': filename,
        'folderName': folder_name,
        'path': f'/api/files/{username}/{folder_name}/{filename}'
    }), 201

def handle_multiple_files_upload(files, username, custom_folder_name=None):
    """处理多个文件上传"""
    print(f"处理多文件上传 - 用户: {username}, 自定义文件夹名称: {custom_folder_name}")

    if not files or len(files) == 0 or files[0].filename == '':
        print("错误: 没有选择文件")
        return jsonify({'message': 'No files selected'}), 400

    # 检查请求中是否有自定义文件夹名称
    if isinstance(custom_folder_name, str) and custom_folder_name.strip():
        print(f"使用自定义文件夹名称: {custom_folder_name.strip()}")
        # 创建唯一文件夹，使用自定义名称
        folder_path, folder_name = create_unique_folder(username, prefix="images", custom_name=custom_folder_name.strip())
    else:
        print("使用时间戳创建文件夹")
        # 使用时间戳创建文件夹
        folder_path, folder_name = create_unique_folder(username, "images")

    print(f"创建的文件夹路径: {folder_path}")
    print(f"创建的文件夹名称: {folder_name}")

    images_folder = os.path.join(folder_path, 'images')

    uploaded_files = []
    image_count = 0

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # 如果是图片，直接保存到images子文件夹
            file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
            if file_type in ['png', 'jpg', 'jpeg', 'gif']:
                image_path = os.path.join(images_folder, filename)
                file.save(image_path)
                image_count += 1
            else:
                # 非图片文件保存到主文件夹
                file_path = os.path.join(folder_path, filename)
                file.save(file_path)

            uploaded_files.append({
                'filename': filename,
                'path': f'/api/files/{username}/{folder_name}/{filename}'
            })

    if uploaded_files:
        return jsonify({
            'message': f'{len(uploaded_files)} files uploaded successfully',
            'files': uploaded_files,
            'folderName': folder_name,
            'imageCount': image_count
        }), 201

    return jsonify({'message': 'No valid files to upload'}), 400

def handle_folder_upload(files, username, custom_folder_name=None):
    """处理文件夹上传"""
    if not files or len(files) == 0 or files[0].filename == '':
        return jsonify({'message': 'No files selected'}), 400

    # 从第一个文件的路径中提取文件夹名称
    first_file_path = files[0].filename
    original_folder_name = first_file_path.split('/')[0] if '/' in first_file_path else 'folder'

    # 检查请求中是否有自定义文件夹名称
    if isinstance(custom_folder_name, str) and custom_folder_name.strip():
        # 创建唯一文件夹，使用自定义名称
        folder_path, folder_name = create_unique_folder(username, prefix="folder", custom_name=custom_folder_name.strip())
    else:
        # 使用时间戳创建文件夹
        folder_path, folder_name = create_unique_folder(username, "folder")

    images_folder = os.path.join(folder_path, 'images')

    uploaded_files = []
    image_count = 0

    for file in files:
        if file and allowed_file(file.filename):
            # 处理文件夹结构
            relative_path = file.filename
            filename = os.path.basename(relative_path)
            inner_folder_path = os.path.dirname(relative_path)

            # 创建内部文件夹结构
            if inner_folder_path:
                full_inner_folder_path = os.path.join(folder_path, inner_folder_path)
                os.makedirs(full_inner_folder_path, exist_ok=True)
                file_path = os.path.join(full_inner_folder_path, filename)
            else:
                file_path = os.path.join(folder_path, filename)

            # 如果是图片，直接保存到images子文件夹
            file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
            if file_type in ['png', 'jpg', 'jpeg', 'gif']:
                image_path = os.path.join(images_folder, filename)
                file.save(image_path)
                image_count += 1
            else:
                # 非图片文件保存到原有的文件夹结构
                file.save(file_path)

            uploaded_files.append({
                'filename': relative_path,
                'path': f'/api/files/{username}/{folder_name}/{relative_path}'
            })

    if uploaded_files:
        return jsonify({
            'message': f'{len(uploaded_files)} files uploaded successfully',
            'files': uploaded_files,
            'folderName': folder_name,
            'originalFolderName': original_folder_name,
            'imageCount': image_count
        }), 201

    return jsonify({'message': 'No valid files to upload'}), 400

def get_file_info(username, filename):
    """获取单个文件的信息"""
    user_dir = get_user_directory(username)
    file_path_on_disk = os.path.join(user_dir, filename)

    if not os.path.exists(file_path_on_disk) or not os.path.isfile(file_path_on_disk):
        return None

    stat = os.stat(file_path_on_disk)
    return {
        'name': filename,
        'path': f'/api/files/{username}/{filename}',
        'size': stat.st_size,
        'type': filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown',
        'created_time': stat.st_ctime,
        'folder': None
    }

def save_point_cloud_file(file, username):
    """直接保存点云文件到用户根目录"""
    user_dir = get_user_directory(username)
    filename = secure_filename(file.filename)
    
    # 确保文件扩展名是.ply或.splat
    if not (filename.endswith('.ply') or filename.endswith('.splat')):
        raise ValueError("Invalid file type. Only .ply and .splat are allowed.")
        
    file_path = os.path.join(user_dir, filename)
    
    # 如果文件已存在，可以考虑添加时间戳或直接覆盖
    if os.path.exists(file_path):
        # 简单起见，这里直接覆盖
        print(f"File {filename} already exists. Overwriting.")
        
    file.save(file_path)
    print(f"Point cloud file saved to: {file_path}")
    
    return file_path

def get_user_file(username, filename):
    """获取用户文件"""
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], username)

    try:
        # 检查文件是否存在
        file_path = os.path.join(user_dir, filename)
        if not os.path.exists(file_path):
            return {'message': 'File not found'}, 404

        # 获取文件所在的目录
        dir_path = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)

        # 如果目录是用户根目录，直接发送文件
        if dir_path == user_dir:
            response = send_from_directory(user_dir, base_name)
        else:
            # 否则，从相对路径发送文件
            relative_dir = os.path.relpath(dir_path, user_dir)
            response = send_from_directory(os.path.join(user_dir, relative_dir), base_name)

        # 添加CORS头，允许所有来源访问文件
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')

        return response
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return {'message': 'Error serving file'}, 500

def list_user_files(username):
    """列出用户所有文件"""
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], username)

    # 确保用户目录存在
    os.makedirs(user_dir, exist_ok=True)

    # 即使创建了目录，也再次检查一下
    if not os.path.exists(user_dir):
        return jsonify({'message': 'User directory not found', 'files': []}), 404

    files = []
    for root, _, filenames in os.walk(user_dir):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, user_dir)

            # 获取文件所在的顶级文件夹
            top_folder = relative_path.split(os.path.sep)[0] if os.path.sep in relative_path else None

            files.append({
                'filename': relative_path,
                'path': f'/api/files/{username}/{relative_path}',
                'size': os.path.getsize(file_path),
                'type': os.path.splitext(filename)[1][1:] if '.' in filename else 'unknown',
                'folder': top_folder
            })

    return jsonify({'files': files}), 200

def list_user_folders(username):
    """列出用户所有文件夹"""
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], username)

    # 确保用户目录存在
    os.makedirs(user_dir, exist_ok=True)

    if not os.path.exists(user_dir):
        return jsonify({'message': 'User directory not found', 'folders': []}), 404

    folders = []
    for item in os.listdir(user_dir):
        item_path = os.path.join(user_dir, item)
        # 过滤掉 _colmap 后缀的文件夹和 point_cloud_results 文件夹
        if os.path.isdir(item_path) and item != 'point_cloud_results' and not item.endswith('_colmap'):
            # 检查是否有images子文件夹
            images_folder = os.path.join(item_path, 'images')
            has_images = os.path.exists(images_folder) and os.path.isdir(images_folder)
            image_count = 0

            if has_images:
                image_count = len([f for f in os.listdir(images_folder)
                                  if os.path.isfile(os.path.join(images_folder, f))
                                  and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])

            folders.append({
                'name': item,
                'path': f'/api/files/{username}/{item}',
                'created_time': os.path.getctime(item_path),
                'has_images': has_images,
                'image_count': image_count
            })

    # 按创建时间降序排序
    folders.sort(key=lambda x: x['created_time'], reverse=True)

    return jsonify({'folders': folders}), 200

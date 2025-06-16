from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, decode_token
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import timedelta, datetime
import file_handler
from point_cloud import point_cloud_bp
from training import training_bp
import video_processor
import jwt as jwt_lib
import json
import logging
import eventlet

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, instance_path=os.path.join(basedir, 'instance'))
os.makedirs(app.instance_path, exist_ok=True)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')  # Change in production
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'query_string']  # 允许从URL参数获取token
app.config['JWT_QUERY_STRING_NAME'] = 'token'  # URL参数名称
app.config['JWT_HEADER_NAME'] = 'Authorization'  # 头部名称
app.config['JWT_HEADER_TYPE'] = 'Bearer'  # 头部类型前缀

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 1GB max upload size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 配置CORS
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}}, supports_credentials=True)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Register blueprints
app.register_blueprint(point_cloud_bp, url_prefix='/api/point-cloud')
app.register_blueprint(training_bp, url_prefix='/api/training')


# Create database tables
def init_db():
    """初始化数据库"""
    with app.app_context():
        # 只创建不存在的表，不删除现有数据
        db.create_all()
# Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    # Validate input
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400

    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 409

    # Create new user
    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password_hash=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    try:

        data = request.get_json()        
        if not data:
            print("错误: 没有接收到JSON数据")
            return jsonify({'message': 'No JSON data received'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        
        if not username or not password:
            print("错误: 用户名或密码为空")
            return jsonify({'message': 'Username and password required'}), 400
        user = User.query.filter_by(username=username).first()
        print(f"数据库查找用户结果: {user}")
        
        if user:
            password_check = check_password_hash(user.password_hash, password)    
            if password_check:
                access_token = create_access_token(identity=str(user.id))
                return jsonify({
                    'access_token': access_token,
                    'username': username
                }), 200
            else:
                return jsonify({'message': 'Invalid password'}), 401
        else:
            return jsonify({'message': 'User not found'}), 401
            
    except Exception as e:
        print(f"登录异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Login failed'}), 500

@app.route('/api/user', methods=['GET'])
@jwt_required()
def get_user():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if user:
        return jsonify({'username': user.username}), 200
    else:
        return jsonify({'message': 'User not found'}), 404

@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if user:
        return jsonify({'message': f'Hello, {user.username}! This is a protected route.'}), 200
    else:
        return jsonify({'message': 'User not found'}), 404

@app.route('/api/check-auth', methods=['GET'])
@jwt_required(optional=True)
def check_auth():
    current_user_id = get_jwt_identity()
    if current_user_id:
        user = User.query.get(int(current_user_id))
        if user:
            return jsonify({
                'authenticated': True,
                'username': user.username
            }), 200
        else:
            return jsonify({
                'authenticated': False,
                'message': 'User not found'
            }), 200
    else:
        return jsonify({
            'authenticated': False
        }), 200

@app.route('/api/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """验证token有效性的接口"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        if user:
            return jsonify({
                'valid': True,
                'username': user.username,
                'user_id': current_user_id
            }), 200
        else:
            return jsonify({
                'valid': False,
                'message': 'User not found'
            }), 401
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': 'Token verification failed'
        }), 401

# 获取用户个人信息
@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404 
    return jsonify({
        'username': user.username,
        'email': user.email if hasattr(user, 'email') else '',
        'nickname': user.nickname if hasattr(user, 'nickname') else ''
    })

# 更新用户个人信息
@app.route('/api/user/profile', methods=['PUT'])
@jwt_required()
def update_user_profile():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    
    # 更新用户信息
    if 'email' in data:
        user.email = data['email']
    if 'nickname' in data:
        user.nickname = data['nickname']
    
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'})

# 修改密码
@app.route('/api/user/password', methods=['PUT'])
@jwt_required()
def update_password():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    if not data or not data.get('currentPassword') or not data.get('newPassword'):
        return jsonify({'message': 'Missing required fields'}), 400

    # 验证当前密码
    if not check_password_hash(user.password_hash, data['currentPassword']):
        return jsonify({'message': 'Current password is incorrect'}), 401

    # 更新密码
    user.password_hash = generate_password_hash(data['newPassword'])
    db.session.commit()
    return jsonify({'message': 'Password updated successfully'})

# 添加全局OPTIONS请求处理
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    print(f"OPTIONS request for path: /api/{path}")
    return '', 200

# 文件上传路由
@app.route('/api/upload', methods=['POST'])
@jwt_required()
def upload_file():
    # 从JWT token获取用户ID
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'message': 'User not found'}), 404
    current_user = user.username

    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    return file_handler.handle_single_file_upload(request.files['file'], current_user)

@app.route('/api/upload-video', methods=['POST'])
@jwt_required()
def upload_video():
    # 从JWT token获取用户ID
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'message': 'User not found'}), 404
    current_user = user.username

    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    # 获取帧提取参数
    extract_frames = request.form.get('extract_frames', 'false').lower() == 'true'
    extract_all_frames = request.form.get('extract_all_frames', 'false').lower() == 'true'

    try:
        frame_rate = int(request.form.get('frame_rate', '1'))
    except (ValueError, TypeError):
        frame_rate = 1

    custom_folder_name = request.args.get('custom_folder_name') or request.form.get('custom_folder_name')
    print(f"视频上传 - 自定义文件夹名称 (URL 参数或表单): {custom_folder_name}")

    # 处理视频上传
    result = video_processor.handle_video_upload(
        request.files['file'],
        current_user,
        extract_frames=extract_frames,
        frame_rate=frame_rate,
        extract_all_frames=extract_all_frames,
        custom_folder_name=custom_folder_name
    )

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@app.route('/api/upload-multiple', methods=['POST'])
@jwt_required()
def upload_multiple_files():
    # 从JWT token获取用户ID
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'message': 'User not found'}), 404
    current_user = user.username

    if 'files[]' not in request.files:
        return jsonify({'message': 'No files part in the request'}), 400

    # 获取自定义文件夹名称（如果有）
    # 首先尝试从 URL 参数获取，然后尝试从表单数据获取
    custom_folder_name = request.args.get('custom_folder_name') or request.form.get('custom_folder_name')
    print(f"自定义文件夹名称 (URL 参数或表单): {custom_folder_name}")

    return file_handler.handle_multiple_files_upload(
        request.files.getlist('files[]'),
        current_user,
        custom_folder_name=custom_folder_name
    )

@app.route('/api/upload-folder', methods=['POST'])
@jwt_required()
def upload_folder():
    # 从JWT token获取用户ID
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'message': 'User not found'}), 404
    current_user = user.username

    if 'files[]' not in request.files:
        return jsonify({'message': 'No files part in the request'}), 400

    # 获取自定义文件夹名称（如果有）
    # 首先尝试从 URL 参数获取，然后尝试从表单数据获取
    custom_folder_name = request.args.get('custom_folder_name') or request.form.get('custom_folder_name')
    print(f"文件夹上传 - 自定义文件夹名称 (URL 参数或表单): {custom_folder_name}")

    try:
        # 处理文件夹上传
        result = file_handler.handle_folder_upload(
            request.files.getlist('files[]'),
            current_user,
            custom_folder_name=custom_folder_name
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

@app.route('/api/upload_point_cloud/<username>', methods=['POST'])
def upload_point_cloud_file(username):
    """处理单个点云文件上传"""
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    if file:
        try:
            # 使用新的处理函数直接保存到用户根目录
            file_handler.save_point_cloud_file(file, username)
            # 获取并返回新上传文件的完整信息
            file_info = file_handler.get_file_info(username, file.filename)
            return jsonify({
                'message': 'Point cloud file uploaded successfully',
                'file': file_info
            }), 200
        except Exception as e:
            return jsonify({'message': str(e)}), 500
    
    return jsonify({'message': 'File upload failed'}), 400

@app.route('/api/files/<username>/<path:filename>', methods=['GET'])
def get_file(username, filename):
    response = file_handler.get_user_file(username, filename)
    if isinstance(response, Response):
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
    return response

@app.route('/api/files/<username>', methods=['GET'])
# 移除 JWT 认证要求
def list_files(username):
    return file_handler.list_user_files(username)

@app.route('/api/folders/<username>', methods=['GET'])
# 移除 JWT 认证要求
def list_folders(username):
    return file_handler.list_user_folders(username)

@app.route('/api/folders/<username>/<path:folder_name>', methods=['DELETE'])
@jwt_required()
def delete_folder_route(username, folder_name):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    # 安全检查：确保当前登录用户与请求删除的文件夹所属用户一致
    if not user or user.username != username:
        return jsonify({'message': 'Forbidden: You can only delete your own folders.'}), 403
    
    response_data, status_code = _delete_folder_logic(username, folder_name)
    return jsonify(response_data), status_code

def _delete_folder_logic(username, folder_name):
    """提取出的核心删除逻辑，供HTTP和WebSocket调用。返回(dict, status_code)元组"""
    try:
        # 根据错误提示，添加缺少的folder_type参数，默认为None
        result = file_handler.delete_user_folder(username, folder_name, folder_type=None)
        return result, 200
    except FileNotFoundError:
        return {'message': 'Folder not found'}, 404
    except Exception as e:
        app.logger.error(f"Error deleting folder {folder_name} for user {username}: {e}")
        return {'message': f'An error occurred: {str(e)}'}, 500

@app.route('/api/results/<username>/<path:folder_name>', methods=['GET'])
@jwt_required()
def list_result_files_route(username, folder_name):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user or user.username != username:
        return jsonify({'message': 'Forbidden'}), 403

    try:
        result = file_handler.list_result_files_in_folder(username, folder_name)
        return jsonify(result), 200
    except FileNotFoundError:
        return jsonify({'message': 'Result folder not found'}), 404
    except Exception as e:
        app.logger.error(f"Error listing result files for {folder_name}: {e}")
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('delete_folder')
def handle_delete_folder(data):
    username = data.get('username')
    folder_name = data.get('folderName')
    folder_type = data.get('folderType', 'models')  # 前端应提供类型，默认为 'models'
    
    if not all([username, folder_name, folder_type]):
        emit('delete_folder_response', {'success': False, 'error': 'Missing required data.'})
        return

    logger.info(f"User '{username}' requested to delete folder '{folder_name}' of type '{folder_type}' via WebSocket.")

    try:
        # 调用 file_handler 中的删除函数，并传递 folder_type
        message = file_handler.delete_user_folder(username, folder_name, folder_type)
        emit('delete_folder_response', {'success': True, 'message': message})
        logger.info(f"Successfully deleted folder '{folder_name}' for user '{username}'.")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to delete folder '{folder_name}' for user '{username}': {e}")
        emit('delete_folder_response', {'success': False, 'error': str(e)})
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting folder '{folder_name}': {e}")
        emit('delete_folder_response', {'success': False, 'error': 'An unexpected error occurred.'})

@socketio.on('delete_training_result')
def handle_delete_training_result(data):
    """处理通过WebSocket删除训练结果文件夹的请求"""
    token = data.get('token')
    folder_name = data.get('folder_name')

    if not token:
        return {'status': 'error', 'message': 'Missing authentication token.'}

    try:
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        user = User.query.get(int(user_id))
        
        if not user:
            return {'status': 'error', 'message': 'User not found.'}
        
        username = user.username
        print(f"User '{username}' requested to delete training result '{folder_name}' via WebSocket.")

        success, message = file_handler.delete_training_output_folder(username, folder_name)
        
        if success:
            print(f"Successfully deleted training result '{folder_name}' for user '{username}'.")
            # 广播训练结果列表已更新 (可以使用与文件夹更新相同的事件)
            socketio.emit('folders_updated', {'username': username, 'type': 'training_results'})
            return {'status': 'success', 'message': message}
        else:
            print(f"Failed to delete training result '{folder_name}' for user '{username}': {message}")
            return {'status': 'error', 'message': message}

    except jwt_lib.ExpiredSignatureError:
        return {'status': 'error', 'message': 'Token has expired.'}
    except jwt_lib.InvalidTokenError:
        return {'status': 'error', 'message': 'Invalid token.'}
    except Exception as e:
        print(f"An unexpected error occurred during training result deletion: {e}")
        return {'status': 'error', 'message': f'An unexpected error occurred: {e}'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    nickname = db.Column(db.String(80), nullable=True)

    def __init__(self, username, password_hash, email=None, nickname=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.nickname = nickname

    def __repr__(self):
        return f'<User {self.username}>'

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)

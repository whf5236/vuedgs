from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, decode_token
# Socket.IO import removed
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import timedelta, datetime
import file_handler
from point_cloud import point_cloud_bp
from training import training_bp
import video_processor
import jwt as jwt_lib
import json

# Initialize Flask app
app = Flask(__name__)
# 配置CORS，允许所有来源访问
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}}, supports_credentials=True)

# Socket.IO initialization removed

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

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Socket.IO client storage removed

# Register blueprints
app.register_blueprint(point_cloud_bp, url_prefix='/api/point-cloud')
app.register_blueprint(training_bp, url_prefix='/api/training')


# JWT 回调函数
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    # 使用参数以避免IDE警告
    print(f"Checking token: {jwt_payload}, header: {jwt_header}")
    return False

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    print(f"Unauthorized: {callback}")
    return jsonify({
        'status': 'error',
        'message': f'Unauthorized: {callback}',
        'code': 401
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(callback):
    print(f"Invalid token: {callback}")
    return jsonify({
        'status': 'error',
        'message': f'Invalid token: {callback}',
        'code': 401
    }), 401

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
        # 获取原始请求数据
        raw_data = request.get_data()
        print(f"原始请求数据: {raw_data}") 
        data = request.get_json()
        print(f"解析后的JSON数据: {data}")
        print(f"请求Content-Type: {request.content_type}")
        print(f"请求Headers: {dict(request.headers)}")
        
        if not data:
            print("错误: 没有接收到JSON数据")
            return jsonify({'message': 'No JSON data received'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        print(f"提取的用户名: '{username}', 密码: '{password}'")
        
        if not username or not password:
            print("错误: 用户名或密码为空")
            return jsonify({'message': 'Username and password required'}), 400
        
        user = User.query.filter_by(username=username).first()
        print(f"数据库查找用户结果: {user}")
        
        if user:
            print(f"找到用户: {user.username}, ID: {user.id}")
            print(f"用户密码哈希: {user.password_hash[:20]}...")
            
            password_check = check_password_hash(user.password_hash, password)
            print(f"密码验证结果: {password_check}")
            
            if password_check:
                access_token = create_access_token(identity=str(user.id))
                print(f"登录成功，用户: {username}, Token: {access_token[:20]}...")
                return jsonify({
                    'access_token': access_token,
                    'username': username
                }), 200
            else:
                print(f"密码验证失败，用户: {username}")
                return jsonify({'message': 'Invalid password'}), 401
        else:
            print(f"用户不存在: {username}")
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
    
    # 从数据库中获取用户信息
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

    # 获取自定义文件夹名称（如果有）
    # 首先尝试从 URL 参数获取，然后尝试从表单数据获取
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
# 移除 JWT 认证要求
def get_file(username, filename):
    # 不再检查用户身份
    # 添加缓存控制头，防止缓存问题
    response = file_handler.get_user_file(username, filename)
    # 只对 Response 对象添加 headers
    if isinstance(response, Response):
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
    return response

@app.route('/api/files/<username>', methods=['GET'])
# 移除 JWT 认证要求
def list_files(username):
    # 不再检查用户身份
    return file_handler.list_user_files(username)

@app.route('/api/folders/<username>', methods=['GET'])
# 移除 JWT 认证要求
def list_folders(username):
    # 不再检查用户身份
    return file_handler.list_user_folders(username)



if __name__ == '__main__':
    print("正在初始化数据库...")
    init_db()
    print(f"JWT_TOKEN_LOCATION: {app.config['JWT_TOKEN_LOCATION']}")
    print(f"JWT_HEADER_NAME: {app.config['JWT_HEADER_NAME']}")
    print(f"JWT_HEADER_TYPE: {app.config['JWT_HEADER_TYPE']}")
    
    app.run(debug=False, host='0.0.0.0', port=5000)

class WebSocketClient {
  constructor() {
    this.ws = null;
    this.url = '';
    this.userId = '';
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.isConnecting = false;
    this.isConnected = false;
    
    // 错误处理标志
    this.errorHandled = false;
    this.resolved = false;
    
    // 消息回调映射
    this.messageHandlers = new Map();
    this.pendingRequests = new Map();
    this.requestId = 0;
    
    // 事件回调
    this.onConnect = null;
    this.onDisconnect = null;
    this.onMessage = null;
    this.onError = null;
    
    // 心跳检测
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
  }
  
  connect(url, userId) {
    if (this.isConnecting || this.isConnected) {
      console.log('WebSocket已连接或正在连接中');
      return Promise.resolve();
    }
    
    this.url = url;
    this.userId = userId;
    this.isConnecting = true;
    
    // 重置错误处理标志
    this.errorHandled = false;
    this.resolved = false;
    
    return new Promise((resolve, reject) => {
      try {
        console.log(`连接到WebSocket服务器: ${url}`);
        this.ws = new WebSocket(url);
        
        this.ws.onopen = () => {
          console.log('WebSocket连接已建立');
          this.isConnecting = false;
          this.isConnected = true;
          this.reconnectAttempts = 0;
          
          // 发送认证消息
          this.send({
            type: 'auth',
            user_id: this.userId
          });
          
          // 启动心跳检测
          this.startHeartbeat();
          
          if (this.onConnect) {
            this.onConnect();
          }
          
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('解析WebSocket消息失败:', error);
          }
        };
        
        this.ws.onclose = (event) => {
          console.log('WebSocket连接已关闭:', event.code, event.reason);
          this.isConnecting = false;
          this.isConnected = false;
          this.stopHeartbeat();
          
          if (this.onDisconnect) {
            this.onDisconnect(event);
          }
          
          // 自动重连
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnect();
          }
        };
        
        this.ws.onerror = (error) => {
          const errorMsg = error?.message || error?.type || 'WebSocket连接错误';
          console.error('WebSocket错误:', errorMsg);
          console.error('连接URL:', this.url);
          console.error('错误详情:', error);
          console.error('可能的原因: 1) WebSocket服务器未启动 2) 端口被占用 3) 网络连接问题 4) 后端服务器未运行');
          this.isConnecting = false;
          
          // 防止重复调用错误处理
          if (this.onError && !this.errorHandled) {
            this.errorHandled = true;
            this.onError(new Error(errorMsg));
          }
          
          if (!this.resolved) {
            this.resolved = true;
            reject(new Error(errorMsg));
          }
        };
        
      } catch (error) {
        const errorMsg = error?.message || error?.type || '创建WebSocket连接失败';
        console.error('创建WebSocket连接失败:', errorMsg);
        this.isConnecting = false;
        reject(new Error(errorMsg));
      }
    });
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
    this.isConnecting = false;
    this.stopHeartbeat();
  }
  
  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('达到最大重连次数，停止重连');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`${delay}ms后尝试第${this.reconnectAttempts}次重连`);
    
    setTimeout(() => {
      this.connect(this.url, this.userId);
    }, delay);
  }
  
  send(message) {
    if (!this.isConnected || !this.ws) {
      console.warn('WebSocket未连接，无法发送消息');
      return false;
    }
    
    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('发送WebSocket消息失败:', error);
      return false;
    }
  }
  
  // 发送请求并等待响应
  sendRequest(message, timeout = 10000) {
    return new Promise((resolve, reject) => {
      if (!this.isConnected) {
        reject(new Error('WebSocket未连接'));
        return;
      }
      
      const requestId = ++this.requestId;
      message.request_id = requestId;
      
      // 设置超时
      const timeoutId = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error('请求超时'));
      }, timeout);
      
      // 存储请求回调
      this.pendingRequests.set(requestId, {
        resolve,
        reject,
        timeoutId
      });
      
      // 发送消息
      if (!this.send(message)) {
        this.pendingRequests.delete(requestId);
        clearTimeout(timeoutId);
        reject(new Error('发送消息失败'));
      }
    });
  }
  
  handleMessage(data) {
    // 处理心跳响应
    if (data.type === 'pong') {
      this.handlePong();
      return;
    }
    
    // 处理请求响应
    if (data.request_id && this.pendingRequests.has(data.request_id)) {
      const request = this.pendingRequests.get(data.request_id);
      this.pendingRequests.delete(data.request_id);
      clearTimeout(request.timeoutId);
      
      if (data.status === 'success') {
        request.resolve(data);
      } else {
        request.reject(new Error(data.message || '请求失败'));
      }
      return;
    }
    
    // 处理其他消息类型
    if (this.messageHandlers.has(data.type)) {
      const handler = this.messageHandlers.get(data.type);
      handler(data);
    } else {
      console.log('收到未处理的WebSocket消息:', data);
    }
  }
  
  // 注册消息处理器
  onMessage(type, handler) {
    this.messageHandlers.set(type, handler);
  }
  
  // 移除消息处理器
  offMessage(type) {
    this.messageHandlers.delete(type);
  }
  
  startHeartbeat() {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'ping' });
        
        // 设置心跳超时
        this.heartbeatTimeout = setTimeout(() => {
          console.log('心跳超时，断开连接');
          this.disconnect();
        }, 5000);
      }
    }, 30000); // 每30秒发送一次心跳
  }
  
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }
  
  handlePong() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }
  
  // API方法 - 文件相关
  async getFolders(username) {
    return this.sendRequest({
      type: 'get_folders',
      username: username
    });
  }
  
  async getFiles(username) {
    return this.sendRequest({
      type: 'get_files',
      username: username
    });
  }
  
  async uploadFile(username, fileData, fileType) {
    return this.sendRequest({
      type: 'upload_file',
      username: username,
      file_data: fileData,
      file_type: fileType
    });
  }
  
  // API方法 - 点云处理相关
  async getPointCloudResults(username) {
    return this.sendRequest({
      type: 'get_point_cloud_results',
      username: username
    });
  }
  
  async startPointCloudProcessing(username, folderName) {
    return this.sendRequest({
      type: 'start_point_cloud_processing',
      username: username,
      folder_name: folderName
    });
  }
  
  async getPointCloudStatus(taskId) {
    return this.sendRequest({
      type: 'get_point_cloud_status',
      task_id: taskId
    });
  }
  
  async cancelPointCloudProcessing(taskId) {
    return this.sendRequest({
      type: 'cancel_point_cloud_processing',
      task_id: taskId
    });
  }
  
  // API方法 - 训练相关
  async getTrainingResults(username) {
    return this.sendRequest({
      type: 'get_training_results',
      username: username
    });
  }
  
  async startTraining(username, params) {
    return this.sendRequest({
      type: 'start_training',
      username: username,
      params: params
    });
  }
  
  async getTrainingStatus(taskId) {
    return this.sendRequest({
      type: 'get_training_status',
      task_id: taskId
    });
  }
  
  async getActiveTasks(username) {
    return this.sendRequest({
      type: 'get_active_tasks',
      username: username
    });
  }
  
  async cancelTraining(taskId) {
    return this.sendRequest({
      type: 'cancel_training',
      task_id: taskId
    });
  }
  
  // API方法 - 可视化相关
  async getVisualizationStatus() {
    return this.sendRequest({
      type: 'get_visualization_status'
    });
  }
  
  async renderVisualization(params) {
    return this.sendRequest({
      type: 'render_visualization',
      params: params
    });
  }
  
  async getVisualizationHistory(metric, maxPoints) {
    return this.sendRequest({
      type: 'get_visualization_history',
      metric: metric,
      max_points: maxPoints
    });
  }
  
  async controlVisualization(action, params) {
    return this.sendRequest({
      type: 'control_visualization',
      action: action,
      params: params
    });
  }
  
  async setCameraPosition(position) {
    return this.sendRequest({
      type: 'set_camera_position',
      position: position
    });
  }
  
  // API方法 - 用户认证相关
  async login(username, password) {
    return this.sendRequest({
      type: 'login',
      username: username,
      password: password
    });
  }
  
  async register(username, password) {
    return this.sendRequest({
      type: 'register',
      username: username,
      password: password
    });
  }
  
  async checkAuth(token) {
    return this.sendRequest({
      type: 'check_auth',
      token: token
    });
  }
  
  async connect() {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('No token available');
    }

    this.socket = io(process.env.VUE_APP_WS_URL, {
      auth: {
        token
      }
    });

    return new Promise((resolve, reject) => {
      this.socket.on('connect', () => {
        this.socket.emit('auth', { token });
        resolve();
      });

      this.socket.on('connect_error', (error) => {
        reject(error);
      });
    });
  }
}

// 创建全局实例
const wsClient = new WebSocketClient();

export default wsClient;
export { WebSocketClient };
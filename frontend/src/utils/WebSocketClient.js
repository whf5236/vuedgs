import { io } from 'socket.io-client';

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.messageHandlers = new Map();
  }
  
  connect(url, token) {
    if (this.socket && this.socket.connected) {
      console.log('Socket.IO 已经连接。');
      return Promise.resolve();
    }
    
    return new Promise((resolve, reject) => {
      this.socket = io(url, {
        auth: {
          token: token
        },
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });

      this.socket.on('connect', () => {
        console.log('Socket.IO 连接成功, ID:', this.socket.id);
        this.registerDefaultHandlers();
          resolve();
      });
        
      this.socket.on('connect_error', (error) => {
        console.error('Socket.IO 连接错误:', error);
        reject(error);
      });

      this.socket.on('disconnect', (reason) => {
        console.log('Socket.IO 连接断开:', reason);
      });
    });
  }
  
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
  
  isConnected() {
      return this.socket && this.socket.connected;
  }

  // 使用emit发送事件
  emit(eventName, data) {
    if (!this.isConnected()) {
      console.warn('Socket.IO 未连接，无法发送事件');
      return;
    }
    this.socket.emit(eventName, data);
  }
  
  // 发送请求并等待响应 (使用 acknowledgements)
  emitWithAck(eventName, data, timeout = 10000) {
    return new Promise((resolve, reject) => {
      if (!this.isConnected()) {
        return reject(new Error('Socket.IO 未连接'));
      }
      
      this.socket.timeout(timeout).emit(eventName, data, (err, response) => {
        if (err) {
          return reject(new Error('请求超时或无响应'));
        }
        if (response && response.status === 'success') {
          resolve(response);
      } else {
          const errorMessage = response ? response.message : '请求失败，未收到有效响应。';
          reject(new Error(errorMessage));
      }
      });
    });
  }
  
  // 注册消息处理器
  on(eventName, handler) {
    if (this.socket) {
        this.socket.on(eventName, handler);
    }
    this.messageHandlers.set(eventName, handler);
  }
  
  // 移除消息处理器
  off(eventName) {
    if (this.socket) {
        this.socket.off(eventName);
    }
    this.messageHandlers.delete(eventName);
  }
  
  registerDefaultHandlers() {
      this.messageHandlers.forEach((handler, eventName) => {
          this.socket.on(eventName, handler);
    });
  }
  
  // --- API 方法 ---
  
  async deleteFolder(username, folderName) {
    const token = localStorage.getItem('token');
      return this.emitWithAck('delete_folder', {
          username,
          folder_name: folderName,
          token // 传递token供后端验证
    });
  }
  
  async deleteTrainingResult(username, folderName) {
    const token = localStorage.getItem('token');
    return this.emitWithAck('delete_training_result', {
        username,
        folder_name: folderName,
        token
    });
  }
}

// 创建全局实例
const wsClient = new WebSocketClient();

export default wsClient;
export { WebSocketClient };
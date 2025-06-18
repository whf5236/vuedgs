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
        this.registerDefaultHandlers();
          resolve();
      });
        
      this.socket.on('connect_error', (error) => {
        console.error('Socket.IO 连接错误:', error);  // 这里应该显示错误信息
        reject(error);
      });

      this.socket.on('disconnect', (reason) => {
        console.log('Socket.IO 连接断开:', reason);  // 这里应该显示断开原因
      });
    });
  }

  registerDefaultHandlers() {
    // Placeholder for any default event handlers
    console.log('WebSocketClient: Default handlers can be registered here.');
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

  on(eventName, callback) {
    if (this.socket) {
      this.socket.on(eventName, callback);
    } else {
      console.warn('Socket.IO 未连接，无法监听事件:', eventName);
    }
  }

  off(eventName, callback) {
    if (this.socket) {
      if (callback) {
        this.socket.off(eventName, callback);
      } else {
        // If no callback is provided, remove all listeners for the event
        this.socket.off(eventName);
      }
    } else {
      console.warn('Socket.IO 未连接，无法移除事件监听:', eventName);
    }
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
 // c:\Users\whf\Desktop\workspace\login_project\frontend\src\utils\WebSocketClient.js
emitWithAck(eventName, data, timeout = 10000) {
  return new Promise((resolve, reject) => {
    if (!this.isConnected()) {
      return reject(new Error('Socket.IO 未连接'));
    }
    
    // Socket.IO ack 回调的第一个参数是 err, 第二个是 data
    this.socket.timeout(timeout).emit(eventName, data, (err, responseData) => { 
      console.log(`收到 ${eventName} ack 回调: err=`, err, `, responseData=`, responseData);
      
      if (err) {
        // 如果 err 存在，说明请求过程中发生错误 (例如超时)
        console.error(`事件 ${eventName} 的 ack 回调错误:`, err);
        return reject(err instanceof Error ? err : new Error(err.message || '请求失败或超时'));
      }
      
      // 即使 err 为 null/undefined，responseData 也可能不存在或不符合预期
      // 后端返回的 {'status': 'success', ...} 或 {'status': 'error', ...} 会在 responseData 中
      if (responseData) {
        resolve(responseData); 
      } else {
        // 这种情况理论上不应该发生，如果后端总是返回一个对象
        // 但作为防御性编程，可以处理一下
        console.warn(`事件 ${eventName} 的 ack 回调未收到预期的响应数据。`);
        reject(new Error('请求成功，但未收到预期的响应数据。'));
      }
    });
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
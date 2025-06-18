class SplatvizWebSocketClient {
  constructor() {
    this.ws = null;
    this.messageHandlers = new Map();
    this.onOpenCallback = null;
    this.onCloseCallback = null;
  }

  connect(url) {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        return resolve();
      }

      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log(`Splatviz WebSocket connected to ${url}`);
        if (this.onOpenCallback) this.onOpenCallback();
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          let message;
          let messageType;

          console.log("[WebSocket] 收到原始消息:", {
            dataType: event.data instanceof Blob ? 'Blob' : typeof event.data,
            size: event.data instanceof Blob ? event.data.size + ' bytes' : event.data.length + ' chars',
            timestamp: new Date().toISOString()
          });

          if (event.data instanceof Blob) {
              message = { type: 'splat_image', data: event.data };
              messageType = 'splat_image';
              console.log("[WebSocket] 解析为图像消息:", { type: messageType, blobSize: event.data.size });
          } else {
              message = JSON.parse(event.data);
              // Assume untyped messages are stats, for backward compatibility.
              messageType = message.type || 'splat_stats';
              console.log("[WebSocket] 解析为JSON消息:", { type: messageType, data: message });
          }
          
          if (this.messageHandlers.has(messageType)) {
              console.log("[WebSocket] 分发消息到处理器:", messageType);
              this.messageHandlers.get(messageType)(message);
          } else {
              console.warn("[WebSocket] 没有找到消息类型的处理器:", messageType);
          }
        } catch(e) {
            console.error("Failed to parse or handle splatviz message:", e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('Splatviz WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('Splatviz WebSocket disconnected.');
        this.ws = null;
        this.messageHandlers.clear(); // Clean up handlers on disconnect
        if (this.onCloseCallback) this.onCloseCallback();
      };
    });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    console.warn('Splatviz WebSocket not connected, cannot send data.');
    return false;
  }

  onMessage(type, handler) {
    this.messageHandlers.set(type, handler);
  }

  offMessage(type) {
    this.messageHandlers.delete(type);
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  onOpen(callback) {
    this.onOpenCallback = callback;
  }

  onClose(callback) {
    this.onCloseCallback = callback;
  }
}

export default new SplatvizWebSocketClient();
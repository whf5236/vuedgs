// 任务状态轮询管理器
export class TaskPollingManager {
  constructor() {
    this.pollingInterval = null;
    this.isPolling = false;
    this.pollingDelay = 2000; // 2秒轮询间隔
  }

  // 开始轮询
  startPolling(pollFunction, onUpdate, onError) {
    if (this.isPolling) {
      console.log('轮询已在进行中');
      return;
    }

    this.isPolling = true;
    console.log('开始状态轮询');

    this.pollingInterval = setInterval(async () => {
      try {
        const result = await pollFunction();
        if (onUpdate) {
          onUpdate(result);
        }
      } catch (error) {
        console.error('轮询过程中发生错误:', error);
        if (onError) {
          onError(error);
        }
        // 发生错误时停止轮询
        this.stopPolling();
      }
    }, this.pollingDelay);
  }

  // 停止轮询
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
      this.isPolling = false;
      console.log('状态轮询已停止');
    }
  }

  // 检查是否正在轮询
  getPollingStatus() {
    return this.isPolling;
  }

  // 设置轮询间隔
  setPollingDelay(delay) {
    this.pollingDelay = delay;
  }

  // 重启轮询
  restartPolling(pollFunction, onUpdate, onError) {
    this.stopPolling();
    setTimeout(() => {
      this.startPolling(pollFunction, onUpdate, onError);
    }, 100);
  }

  // 销毁管理器
  destroy() {
    this.stopPolling();
  }
}
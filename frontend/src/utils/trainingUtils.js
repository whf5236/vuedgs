// 训练相关工具函数
export class TrainingUtils {
  // 获取当前用户名
  static getCurrentUsername() {
    try {
      const userInfo = JSON.parse(localStorage.getItem('userInfo'));
      return userInfo?.username || 'Unknown';
    } catch (error) {
      console.error('获取用户名失败:', error);
      return 'Unknown';
    }
  }

  // 格式化时间戳
  static formatTimestamp(timestamp) {
    if (!timestamp) return '';
    
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (error) {
      console.error('格式化时间戳失败:', error);
      return timestamp;
    }
  }

  // 解析当前任务状态
  static parseCurrentTaskStatus(currentTask) {
    if (!currentTask) {
      return {
        status: 'idle',
        message: '无活动任务',
        progress: 0
      };
    }

    const status = currentTask.status || 'unknown';
    const message = currentTask.message || currentTask.error || '状态未知';
    const progress = currentTask.progress || 0;

    return {
      status,
      message,
      progress,
      taskId: currentTask.task_id,
      startTime: currentTask.start_time,
      endTime: currentTask.end_time
    };
  }

  // 解析迭代次数
  static parseIterationCount(currentTask) {
    if (!currentTask || !currentTask.message) {
      return 0;
    }

    try {
      const match = currentTask.message.match(/Iteration (\d+)/);
      return match ? parseInt(match[1]) : 0;
    } catch (error) {
      console.error('解析迭代次数失败:', error);
      return 0;
    }
  }

  // 计算训练进度百分比
  static calculateProgress(currentIteration, totalIterations) {
    if (!totalIterations || totalIterations <= 0) return 0;
    
    const progress = (currentIteration / totalIterations) * 100;
    return Math.min(Math.max(progress, 0), 100);
  }

  // 验证文件夹选择
  static validateFolderSelection(selectedFolder) {
    if (!selectedFolder) {
      return {
        isValid: false,
        error: '请选择一个文件夹'
      };
    }

    // 可以添加更多验证逻辑
    return {
      isValid: true,
      error: null
    };
  }

  // 格式化文件大小
  static formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // 生成唯一任务ID
  static generateTaskId() {
    return 'task_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // 检查任务是否为活动状态
  static isTaskActive(status) {
    const activeStatuses = ['running', 'starting', 'processing', 'training'];
    return activeStatuses.includes(status?.toLowerCase());
  }

  // 检查任务是否已完成
  static isTaskCompleted(status) {
    const completedStatuses = ['completed', 'finished', 'success', 'done'];
    return completedStatuses.includes(status?.toLowerCase());
  }

  // 检查任务是否失败
  static isTaskFailed(status) {
    const failedStatuses = ['failed', 'error', 'cancelled', 'aborted'];
    return failedStatuses.includes(status?.toLowerCase());
  }

  // 深拷贝对象
  static deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => this.deepClone(item));
    if (typeof obj === 'object') {
      const clonedObj = {};
      for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
          clonedObj[key] = this.deepClone(obj[key]);
        }
      }
      return clonedObj;
    }
  }

  // 防抖函数
  static debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // 节流函数
  static throttle(func, limit) {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
}
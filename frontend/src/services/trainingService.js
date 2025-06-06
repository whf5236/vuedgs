import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

export class TrainingService {
  // 获取文件夹列表
  static async getFolders() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/folders`);
      return response.data;
    } catch (error) {
      console.error('获取文件夹失败:', error);
      throw error;
    }
  }

  // 获取训练结果
  static async getTrainingResults(username) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training/results?username=${username}`);
      return response.data;
    } catch (error) {
      console.error('获取训练结果失败:', error);
      throw error;
    }
  }

  // 启动训练任务
  static async startTraining(taskData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/training/start`, taskData);
      return response.data;
    } catch (error) {
      console.error('启动训练失败:', error);
      throw error;
    }
  }

  // 获取训练状态
  static async getTrainingStatus(username, taskId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training/status/${taskId}?username=${username}`);
      return response.data;
    } catch (error) {
      console.error('获取训练状态失败:', error);
      throw error;
    }
  }

  // 取消训练任务
  static async cancelTraining(username, taskId) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/training/cancel/${taskId}?username=${username}`);
      return response.data;
    } catch (error) {
      console.error('取消训练失败:', error);
      throw error;
    }
  }

  // 重置训练状态
  static async resetTrainingStatus() {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/training/reset`);
      return response.data;
    } catch (error) {
      console.error('重置训练状态失败:', error);
      throw error;
    }
  }

  // 强制重置训练状态
  static async forceResetTrainingStatus() {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/training/force-reset`);
      return response.data;
    } catch (error) {
      console.error('强制重置训练状态失败:', error);
      throw error;
    }
  }

  // 检查活动任务
  static async checkActiveTask(username) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training/active?username=${username}`);
      return response.data;
    } catch (error) {
      console.error('检查活动任务失败:', error);
      throw error;
    }
  }

  // 验证任务状态
  static async validateTaskStatus() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training/validate-status`);
      return response.data;
    } catch (error) {
      console.error('验证任务状态失败:', error);
      throw error;
    }
  }

  // 查看训练结果
  static async viewResults(resultPath) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/training/view-results`, {
        params: { path: resultPath }
      });
      return response.data;
    } catch (error) {
      console.error('查看训练结果失败:', error);
      throw error;
    }
  }

  // 获取点云处理结果
  static async getPointCloudResults(username) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/point-cloud/results?username=${username}`);
      return response.data;
    } catch (error) {
      console.error('获取点云处理结果失败:', error);
      throw error;
    }
  }
}
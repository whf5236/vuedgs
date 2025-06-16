<template>
  <div class="point-cloud-processor">
    <div class="processor-layout">
      <!-- 左侧：文件夹选择 -->
      <div class="glass-card layout-left">
        <div class="card-header">
          <h6 class="m-0"><i class="fas fa-folder me-2"></i> 图片文件夹</h6>
        </div>
        <div class="card-body">
          <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-3">加载文件夹...</p>
          </div>

          <div v-else-if="folders.length === 0" class="text-center py-5">
            <i class="fas fa-folder-open fa-4x text-muted mb-3"></i>
            <p class="text-muted">No image folders found</p>
            <p class="text-muted small">Upload images first in the File Upload tab</p>
          </div>

          <div v-else class="folder-list">
            <div v-for="folder in folders" :key="folder.name" class="folder-item"
              :class="{ 'active': selectedFolder === folder.name }" @click="selectFolder(folder)">
              <div class="folder-icon">
                <i class="fas fa-folder"></i>
              </div>
              <div class="folder-info">
                <div class="folder-name">{{ folder.name }}</div>
                <div class="folder-details">
                  <span><i class="fas fa-image me-1"></i> {{ folder.image_count }} images</span>
                  <span class="ms-2"><i class="fas fa-clock me-1"></i> {{ formatDate(folder.created_time) }}</span>
                </div>
              </div>
              <div class="folder-action">
                <button class="btn btn-sm btn-primary" @click.stop="processFolder(folder)"
                  :disabled="isProcessing || processingFolder === folder.name">
                  <i class="fas" :class="processingFolder === folder.name ? 'fa-spinner fa-spin' : 'fa-play'"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：处理状态和结果 -->
      <div class="glass-card layout-right">
        <div class="card-header">
          <h6 class="m-0"><i class="fas fa-cube me-2"></i> 点云处理</h6>
        </div>
        <div class="card-body">
          <div v-if="!selectedFolder && !currentTask" class="text-center py-5">
            <i class="fas fa-cube fa-4x text-muted mb-3"></i>
            <p class="text-muted">选择文件夹进行处理</p>
            <p class="text-muted small">The processing may take several minutes depending on the number of images</p>
          </div>

          <div v-else-if="currentTask" class="processing-status">
            <h5 class="mb-4">
              Processing: {{ processingFolder }}
              <span class="badge bg-primary ms-2">{{ currentTask.status }}</span>
            </h5>

            <div class="progress mb-4" style="height: 25px;">
              <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar"
                :style="{ width: `${currentTask.progress}%` }" :class="{
                  'bg-success': currentTask.status === 'completed',
                  'bg-danger': currentTask.status === 'failed',
                  'bg-warning': currentTask.status === 'cancelled'
                }">
                {{ currentTask.progress }}%
              </div>
            </div>

            <div class="alert" :class="{
              'alert-info': currentTask.status === 'processing',
              'alert-success': currentTask.status === 'completed',
              'alert-danger': currentTask.status === 'failed',
              'alert-warning': currentTask.status === 'cancelled'
            }">
              <i class="fas" :class="{
                'fa-info-circle': currentTask.status === 'processing',
                'fa-check-circle': currentTask.status === 'completed',
                'fa-exclamation-circle': currentTask.status === 'failed',
                'fa-ban': currentTask.status === 'cancelled'
              }"></i>
              {{ currentTask.message }}
            </div>

            <div v-if="currentTask.status === 'processing'" class="mt-3">
              <button class="btn btn-danger" @click="cancelTask">
                <i class="fas fa-stop me-2"></i> Cancel Processing
              </button>
            </div>

            <div v-if="currentTask.status === 'completed'" class="mt-4">
              <h6 class="mb-3">Processing Results</h6>
              <div class="result-info">
                <p><strong>Processing Time:</strong> {{ formatTime(currentTask.processing_time) }}</p>
                <p><strong>输出文件夹:</strong> {{ currentTask.output_folder }}</p>
              </div>
              <div class="mt-3">
                <button class="btn btn-success me-2" @click="viewResults">
                  <i class="fas fa-eye me-2"></i> View Results
                </button>
                <button class="btn btn-primary" @click="resetTask">
                  <i class="fas fa-redo me-2"></i> Process Another Folder
                </button>
              </div>
            </div>

            <div v-if="currentTask.status === 'failed'" class="mt-4">
              <button class="btn btn-primary" @click="resetTask">
                <i class="fas fa-redo me-2"></i> 重试
              </button>
            </div>
          </div>

          <div v-else-if="selectedFolder" class="folder-details-view">
            <h5 class="mb-4">{{ selectedFolder }}</h5>

            <div class="folder-summary mb-4">
              <div class="row">
                <div class="col-md-6">
                  <div class="info-card">
                    <div class="info-icon">
                      <i class="fas fa-images"></i>
                    </div>
                    <div class="info-content">
                      <div class="info-label">Images</div>
                      <div class="info-value">{{ selectedFolderDetails?.image_count || 0 }}</div>
                    </div>
                  </div>
                </div>
                <div class="col-md-6">
                  <div class="info-card">
                    <div class="info-icon">
                      <i class="fas fa-calendar-alt"></i>
                    </div>
                    <div class="info-content">
                      <div class="info-label">Created</div>
                      <div class="info-value">{{ formatDate(selectedFolderDetails?.created_time) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="processing-options mb-4">
              <h6 class="mb-3">Processing Options</h6>
              <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" v-model="processingOptions.resize" id="resizeOption">
                <label class="form-check-label" for="resizeOption">
                  Generate resized versions of images (recommended)
                </label>
              </div>
            </div>

            <div class="processing-actions">
              <button class="btn btn-primary btn-lg" @click="processSelectedFolder" :disabled="isProcessing">
                <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-play'"></i>
                {{ isProcessing ? 'Processing...' : 'Start Processing' }}
              </button>
              <button class="btn btn-outline-secondary ms-2" @click="cancelSelection" :disabled="isProcessing">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 处理结果列表 -->
    <div class="glass-card mt-4">
      <div class="card-header">
        <h6 class="m-0"><i class="fas fa-history me-2"></i> 处理历史</h6>
      </div>
      <div class="card-body">
        <div v-if="loadingResults" class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <p class="mt-3">Loading processing history...</p>
        </div>

        <div v-else-if="results.length === 0" class="text-center py-4">
          <i class="fas fa-history fa-3x text-muted mb-3"></i>
          <p class="text-muted">No processing history found</p>
        </div>

        <div v-else class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Folder</th>
                <th>Status</th>
                <th>Processing Time</th>
                <th>Processed On</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="result in results" :key="result.task_id || result.name">
                <td>{{ result.source_path ? result.source_path.split('/').pop() : result.name }}</td>
                <td>
                  <span class="badge" :class="{
                    'bg-success': result.status === 'completed',
                    'bg-danger': result.status === 'failed',
                    'bg-warning': result.status === 'cancelled',
                    'bg-secondary': result.status === 'unknown'
                  }">{{ result.status }}</span>
                </td>
                <td>{{ result.processing_time ? formatTime(result.processing_time) : 'N/A' }}</td>
                <td>{{ result.timestamp ? formatDate(result.timestamp) : 'Unknown' }}</td>
                <td>
                  <button class="btn btn-sm btn-outline-primary me-1" @click="viewResultDetails(result)">
                    <i class="fas fa-eye"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <el-dialog v-model="resultsDialogVisible" :title="`'${selectedResultFolder}' 的处理结果`" width="50%" class="glass-dialog">
      <el-table :data="currentResultFiles" stripe style="width: 100%">
        <el-table-column prop="name" label="文件名" sortable />
        <el-table-column prop="size" label="大小" sortable>
          <template #default="scope">
            {{ formatFileSize(scope.row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="modified" label="修改日期" sortable>
          <template #default="scope">
            {{ new Date(scope.row.modified * 1000).toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resultsDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios'
// SocketIOClient import removed
import { eventBus } from '@/utils/eventBus';
import { ElMessage } from 'element-plus';
import { shallowRef } from 'vue';
import { Folder, Delete, Refresh, VideoCamera, Picture, ArrowRight, View, CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue';

export default {
  name: 'PointCloudProcessor',
  data() {
    return {
      loading: true,
      loadingResults: true,
      folders: [],
      results: [],
      selectedFolder: null,
      selectedFolderDetails: null,
      processingFolder: null,
      currentTask: null,
      taskCheckInterval: null,
      processingOptions: {
        resize: true
      },
      error: null,
      processingStatus: {},
      activeTask: null,
      resultsDialogVisible: false,
      currentResultFiles: [],
      selectedResultFolder: '',
    };
  },
  computed: {
    isProcessing() {
      return this.currentTask && this.currentTask.status === 'processing';
    }
  },
  mounted() {
    this.fetchFolders();
    this.fetchResults();

    // 监听自动处理请求
    eventBus.on('process-folder', this.handleAutoProcess);
  },
  beforeUnmount() {
    this.clearTaskCheckInterval();

    // 移除事件监听
    eventBus.off('process-folder', this.handleAutoProcess);
  },
  methods: {
    async fetchFolders(refresh = false) {
      this.loading = true;
      this.error = null;

      try {
        // 检查用户是否已登录
        if (!this.$store.getters.isAuthenticated) {
          this.$message.error('请先登录');
          return;
        }
        const username = this.$store.getters.user?.username;

        let response;

        if (refresh) {
          const httpResponse = await axios.get(`http://localhost:5000/api/folders/${username}`);
          response = { data: httpResponse.data };
        } else {
          const httpResponse = await axios.get(`http://localhost:5000/api/folders/${username}`);
          response = { data: httpResponse.data };
        }

        console.log('获取到的文件夹:', response.data);

        // 过滤出包含图片的文件夹
        this.folders = response.data.folders.filter(folder => folder.has_images) || [];
      } catch (error) {
        console.error('Error fetching folders:', error);
        this.error = 'Failed to load folders. Please try again.';
      } finally {
        this.loading = false;
      }
    },

    async fetchResults() {
      this.loadingResults = true;

      try {
        // 检查用户是否已登录
        if (!this.$store.getters.isAuthenticated) {
          this.$message.error('请先登录');
          return;
        }
        const username = this.$store.getters.user?.username;
        let response;
        // HTTP回退
        const httpResponse = await axios.get(
          `http://localhost:5000/api/point-cloud/results?username=${username}`
        );
        response = { data: httpResponse.data };
        // 设置结果列表
        this.results = response.data.results || [];
      } catch (error) {
        console.error('Error fetching results:', error);
      } finally {
        this.loadingResults = false;
      }
    },

    selectFolder(folder) {
      this.selectedFolder = folder.name;
      this.selectedFolderDetails = folder;
    },

    cancelSelection() {
      this.selectedFolder = null;
      this.selectedFolderDetails = null;
    },

    async processFolder(folder) {
      console.log('处理文件夹:', folder);
      this.processingFolder = folder.name;
      await this.startProcessing(folder.name);
    },

    async processSelectedFolder() {
      if (!this.selectedFolder) return;

      console.log('处理选中的文件夹:', this.selectedFolder, this.selectedFolderDetails);
      this.processingFolder = this.selectedFolder;
      await this.startProcessing(this.selectedFolder);
    },

    async startProcessing(folderName) {
      try {
        // 检查用户是否已登录
        if (!this.$store.getters.isAuthenticated) {
          this.$message.error('请先登录');
          return;
        }
        const username = this.$store.getters.user?.username;
        console.log(`开始处理文件夹: ${folderName}`);
        let response;
        const httpResponse = await axios.post(
          `http://localhost:5000/api/point-cloud/process?username=${username}`,
          { folder_name: folderName },
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );
      response = httpResponse;

      // 设置当前任务
      this.currentTask = {
        task_id: response.data.task_id,
        status: 'processing',
        progress: 0,
        message: 'Starting point cloud processing...',
        folder_name: folderName
      };
      // 开始轮询任务状态
      this.startTaskStatusPolling(response.data.task_id);
    } catch (error) {
      console.error('Error starting processing:', error);
      this.processingFolder = null;
      this.error = 'Failed to start processing. Please try again.';
    }
  },

  startTaskStatusPolling(taskId) {
    // 清除之前的轮询
    this.clearTaskCheckInterval();
    // 设置新的轮询来获取任务状态
    this.taskCheckInterval = setInterval(async () => {
      try {
        // 获取当前登录用户
        let username = this.$store.getters.user?.username;
        // 确保用户名不是 undefined
        if (!username || username === 'undefined') {
          username = 'default_user';
        }

        // 获取任务状态
        let response;

        // 尝试WebSocket获取点云任务状态
        try {
          if (!wsClient.isConnected) {
            await wsClient.connect('ws://localhost:6010', username);
          }
          response = await wsClient.getPointCloudStatus(taskId, username);
        } catch (wsError) {
          console.warn('WebSocket获取点云任务状态失败，回退到HTTP:', wsError);
          // HTTP回退
          const httpResponse = await axios.get(
            `http://localhost:5000/api/point-cloud/status/${taskId}?username=${username}`
          );
          response = { data: httpResponse.data };
        }

        console.log('任务状态:', response.data);

        // 更新任务状态
        this.currentTask = {
          ...this.currentTask,
          ...response.data
        };

        // 如果任务已完成或失败，停止轮询
        if (response.data.status === 'completed' || response.data.status === 'failed' || response.data.status === 'cancelled') {
          // 停止轮询
          this.clearTaskCheckInterval();
          // 刷新结果列表
          this.fetchResults();
          // 通知其他组件刷新文件夹列表
          eventBus.emit('refresh-folders');
          // 如果处理成功完成，发出事件通知训练组件
          if (response.data.status === 'completed') {
            // 使用全局事件总线通知训练组件
            eventBus.emit('point-cloud-processed', {
              folder_name: this.processingFolder,
              output_folder: response.data.output_folder,
              status: 'completed'
            });
          }
        }
      } catch (error) {
        console.error('获取任务状态失败:', error);
        // 如果出错，也停止轮询
        this.clearTaskCheckInterval();
        // 更新任务状态为失败
        this.currentTask = {
          ...this.currentTask,
          status: 'failed',
          message: 'Failed to get task status. Please try again.'
        };
      }
    }, 2000); // 每2秒轮询一次
  },

  clearTaskCheckInterval() {
    if (this.taskCheckInterval) {
      clearInterval(this.taskCheckInterval);
      this.taskCheckInterval = null;
    }
  },

  // 模拟检查任务状态 - 实际项目中不需要这个方法
  async checkTaskStatus(taskId) {
    // 这个方法在我们的模拟中不需要，因为我们直接在startTaskProgressSimulation中更新状态
    console.log('Checking task status:', taskId);
  },

  async cancelTask() {
    if (!this.currentTask || !this.currentTask.task_id) return;

    try {
      // 检查用户是否已登录
      if (!this.$store.getters.isAuthenticated) {
        this.$message.error('请先登录');
        return;
      }
      const username = this.$store.getters.user?.username;

      console.log(`取消任务: ${this.currentTask.task_id}`);

      // 调用后端 API 取消任务
      const response = await axios.post(
        `http://localhost:5000/api/point-cloud/cancel/${this.currentTask.task_id}?username=${username}`
      );
      // 更新任务状态
      this.currentTask.status = 'cancelled';
      this.currentTask.message = 'Task cancelled by user';
      // 停止轮询
      this.clearTaskCheckInterval();
      // 刷新结果列表
      this.fetchResults();

      // 通知其他组件刷新文件夹列表
      eventBus.emit('refresh-folders');
    } catch (error) {
      console.error('取消任务失败:', error);
    }
  },

  resetTask() {
    this.currentTask = null;
    this.processingFolder = null;
    this.selectedFolder = null;
    this.selectedFolderDetails = null;
  },

  async viewResults() {
    const username = this.$store.getters.user?.username;
    if (!username) {
      ElMessage.error('无法获取用户信息');
      return;
    }

    this.selectedResultFolder = this.processingFolder;
    this.currentResultFiles = [];
    this.resultsDialogVisible = true;

    try {
      const response = await axios.get(`http://localhost:5000/api/results/${username}/${this.processingFolder}`, {
        headers: { Authorization: `Bearer ${this.$store.state.token}` }
      });
      this.currentResultFiles = response.data.files || [];
    } catch (error) {
      console.error('获取结果文件失败:', error);
      ElMessage.error(error.response?.data?.message || '无法加载结果文件。');
      this.resultsDialogVisible = false;
    }
  },

  viewResultDetails(result) {
    alert(`Result details for ${result.source_path ? result.source_path.split('/').pop() : result.name}`);
  },

  async handleAutoProcess(folderName) {
    await this.fetchFolders();
    const folder = this.folders.find(f => f.name === folderName);

    if (folder) {
      // 选择并处理文件夹
      this.selectFolder(folder);
      this.processFolder(folder);
    } else {
      console.error(`Folder "${folderName}" not found for auto-processing`);
    }
  },

  formatDate(timestamp) {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  },

  formatTime(seconds) {
    if (!seconds) return 'N/A';

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    if (minutes === 0) {
      return `${remainingSeconds} seconds`;
    } else if (minutes === 1) {
      return `1 minute ${remainingSeconds} seconds`;
    } else {
      return `${minutes} minutes ${remainingSeconds} seconds`;
    }
  },

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  },

  loadFolderByName(folderName) {
    const folder = this.folders.find(f => f.name === folderName);
    if (folder) {
      this.selectFolder(folder);
    } else {
      console.warn(`Folder '${folderName}' not found.`);
      // Maybe refresh folders and try again
      this.fetchFolders(true).then(() => {
        const folder = this.folders.find(f => f.name === folderName);
        if (folder) {
          this.selectFolder(folder);
        }
      });
    }
  }
}
};
</script>

<style scoped>
.point-cloud-processor {
  color: #fff;
}

.processor-layout {
  display: flex;
  gap: 20px;
}
.layout-left {
  flex: 1;
}
.layout-right {
  flex: 2;
}

.glass-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(5px);
  border-radius: 15px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.card-header {
  padding-bottom: 15px;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}
.card-header h6 {
  font-weight: 600;
}

.folder-list .folder-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
}
.folder-list .folder-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
.folder-list .folder-item.active {
  background-color: rgba(78, 115, 223, 0.4);
}

/* General component styling to match the theme */
:deep(.el-button), .btn {
  background-color: rgba(78, 115, 223, 0.5) !important;
  border-color: rgba(78, 115, 223, 0.8) !important;
  color: #fff !important;
}
:deep(.el-button:hover), .btn:hover {
  background-color: rgba(78, 115, 223, 0.7) !important;
}

:deep(.progress-bar) {
    background-color: #4e73df;
}
:deep(.alert) {
    background-color: rgba(0,0,0,0.2);
    border-color: rgba(255,255,255,0.2);
}

:deep(.table) {
  --bs-table-color: #fff;
  --bs-table-striped-color: #fff;
  --bs-table-hover-color: #fff;
  --bs-table-hover-bg: rgba(255,255,255,0.1);
  border-color: rgba(255,255,255,0.2);
}

.info-card {
    background: rgba(0,0,0,0.2);
    padding: 15px;
    border-radius: 8px;
}
</style>

<style>
/* Glass Dialog - not scoped to penetrate el-dialog */
.glass-dialog {
  background: rgba(30, 30, 40, 0.8) !important;
  backdrop-filter: blur(10px) !important;
  border-radius: 15px !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
.glass-dialog .el-dialog__title {
  color: #fff !important;
}
.glass-dialog .el-dialog__headerbtn .el-dialog__close {
  color: #fff !important;
}
.glass-dialog .el-table {
  --el-table-bg-color: transparent !important;
  --el-table-tr-bg-color: transparent !important;
  --el-table-header-bg-color: rgba(255,255,255,0.1) !important;
  --el-table-row-hover-bg-color: rgba(255,255,255,0.05) !important;
  color: #f0f0f0 !important;
}
.glass-dialog .el-table th, .glass-dialog .el-table td {
    background-color: transparent !important;
    color: #f0f0f0 !important;
    border-bottom: 1px solid rgba(255,255,255,0.2) !important;
}
.glass-dialog .el-table th {
  color: #fff !important;
}
</style>

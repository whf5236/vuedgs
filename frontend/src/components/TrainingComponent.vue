<template>
  <div class="training-component">
    <!-- 源文件夹选择区域 -->
    <div class="parameter-section glass-card">
      <h5>
        <i class="fas fa-folder-open me-2"></i>
        源文件夹选择区域
      </h5>
      <div class="source-folder-selector">
        <p class="mb-3">选择一个Colmap处理过的点云文件进行训练:</p>

        <div v-if="loadingFolders" class="text-center py-3">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <p class="mt-2">加载可用文件夹...</p>
        </div>

        <div v-else-if="folders.length === 0" class="text-center py-3">
          <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
          <p class="text-muted">没有可用的文件夹</p>
          <p class="text-muted small">Process images in the Point Cloud Processing tab first</p>
        </div>

        <div v-else class="folder-list">
          <div
            v-for="folder in folders"
            :key="folder.folder_name || folder.name"
            class="folder-item"
            :class="{ 'active': selectedFolder === (folder.folder_name || folder.name) }"
            @click="selectFolder(folder)"
          >
            <div class="folder-icon">
              <i class="fas fa-folder"></i>
            </div>
            <div class="folder-info">
              <div class="folder-name">{{ folder.folder_name || folder.name }}</div>
              <div class="folder-details">
                <span><i class="fas fa-cube me-1"></i> Processed on {{ formatDate(folder.timestamp || folder.created_time) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 训练参数配置区域 -->
    <div class="parameter-section glass-card">
      <h5>
        <i class="fas fa-sliders-h me-2"></i>
        Training Parameters
      </h5>

      <!-- 基本参数 -->
      <div class="parameter-group">
        <h6 class="mb-3">Basic Parameters</h6>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Iterations
              <i class="fas fa-question-circle parameter-help" title="Number of total iterations to train for"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.iterations"
              min="1000"
              max="100000"
            >
            <div class="parameter-description">默认值: 30,000</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              分辨率缩放
              <i class="fas fa-question-circle parameter-help" title="Specifies resolution of the loaded images before training"></i>
            </div>
            <select class="form-select" v-model="trainingParams.resolution">
              <option value="-1">自动 (默认值)</option>
              <option value="1">Original size</option>
              <option value="2">1/2 resolution</option>
              <option value="4">1/4 resolution</option>
              <option value="8">1/8 resolution</option>
            </select>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" v-model="trainingParams.white_background" id="whiteBackground">
              <label class="form-check-label" for="whiteBackground">
                White Background
              </label>
            </div>
            <div class="parameter-description">Use white background instead of black (default)</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              SH Degree
              <i class="fas fa-question-circle parameter-help" title="球鞋函数的阶数 (不超过 3)"></i>
            </div>
            <select class="form-select" v-model.number="trainingParams.sh_degree">
              <option value="0">0 - Lambertian</option>
              <option value="1">1 - Simple directional</option>
              <option value="2">2 - More detailed</option>
              <option value="3">3 - Full detail (default)</option>
            </select>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              数据加载设备
              <i class="fas fa-question-circle parameter-help" title="Specifies where to put the source image data"></i>
            </div>
            <select class="form-select" v-model="trainingParams.data_device">
              <option value="cuda">CUDA (默认)</option>
              <option value="cpu">CPU (减少显存的占用)</option>
            </select>
          </div>

          <div class="col-md-6">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" v-model="trainingParams.eval" id="evalOption">
              <label class="form-check-label" for="evalOption">
                Use Evaluation Split
              </label>
            </div>
            <div class="parameter-description">Use a MipNeRF360-style training/test split for evaluation</div>
          </div>
        </div>
      </div>

      <!-- 学习率参数 -->
      <div class="parameter-group">
        <h6 class="mb-3">学习率参数</h6>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              位置学习率参数 (初始值)
              <i class="fas fa-question-circle parameter-help" title="Initial 3D position learning rate"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.position_lr_init"
                min="0.00001"
                max="0.001"
                step="0.00001"
              >
              <span class="range-value ms-2">{{ trainingParams.position_lr_init }}</span>
            </div>
            <div class="parameter-description">默认值: 0.00016</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              位置学习率参数 (最终值)
              <i class="fas fa-question-circle parameter-help" title="Final 3D position learning rate"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.position_lr_final"
                min="0.0000001"
                max="0.00001"
                step="0.0000001"
              >
              <span class="range-value ms-2">{{ trainingParams.position_lr_final }}</span>
            </div>
            <div class="parameter-description">默认值: 0.0000016</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Feature Learning Rate
              <i class="fas fa-question-circle parameter-help" title="Spherical harmonics features learning rate"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.feature_lr"
                min="0.0001"
                max="0.01"
                step="0.0001"
              >
              <span class="range-value ms-2">{{ trainingParams.feature_lr }}</span>
            </div>
            <div class="parameter-description">默认值: 0.0025</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              不透明度学习率
              <i class="fas fa-question-circle parameter-help" title="Opacity learning rate"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.opacity_lr"
                min="0.001"
                max="0.1"
                step="0.001"
              >
              <span class="range-value ms-2">{{ trainingParams.opacity_lr }}</span>
            </div>
            <div class="parameter-description">默认值: 0.05</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Scaling 学习率
              <i class="fas fa-question-circle parameter-help" title="Scaling learning rate"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.scaling_lr"
                min="0.0001"
                max="0.01"
                step="0.0001"
              >
              <span class="range-value ms-2">{{ trainingParams.scaling_lr }}</span>
            </div>
            <div class="parameter-description">默认值: 0.005</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              旋转学习率
              <i class="fas fa-question-circle parameter-help" title="Rotation learning rate"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.rotation_lr"
                min="0.0001"
                max="0.01"
                step="0.0001"
              >
              <span class="range-value ms-2">{{ trainingParams.rotation_lr }}</span>
            </div>
            <div class="parameter-description">默认值: 0.001</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Position LR Delay Multiplier
              <i class="fas fa-question-circle parameter-help" title="Position learning rate multiplier (cf. Plenoxels)"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.position_lr_delay_mult"
                min="0.001"
                max="0.1"
                step="0.001"
              >
              <span class="range-value ms-2">{{ trainingParams.position_lr_delay_mult }}</span>
            </div>
            <div class="parameter-description">默认值: 0.01</div>  
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Position LR Max Steps
              <i class="fas fa-question-circle parameter-help" title="Number of steps where position learning rate goes from initial to final"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.position_lr_max_steps"
              min="1000"
              max="100000"
            >
            <div class="parameter-description">默认值: 30,000</div>
          </div>
        </div>
      </div>

      <!-- 密度化参数 -->
      <div class="parameter-group">
        <h6 class="mb-3">密集化参数</h6>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Densify From Iteration
              <i class="fas fa-question-circle parameter-help" title="Iteration where densification starts"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.densify_from_iter"
              min="0"
              max="10000"
            >
            <div class="parameter-description">默认值: 500</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              密集化停止迭代轮数
              <i class="fas fa-question-circle parameter-help" title="Iteration where densification stops"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.densify_until_iter"
              min="1000"
              max="30000"
            >
            <div class="parameter-description">默认值: 15,000</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              密集化间隔
              <i class="fas fa-question-circle parameter-help" title="How frequently to densify (iterations)"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.densification_interval"
              min="10"
              max="1000"
            >
            <div class="parameter-description">默认值: 100</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              不透明度重置间隔
              <i class="fas fa-question-circle parameter-help" title="How frequently to reset opacity (iterations)"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.opacity_reset_interval"
              min="100"
              max="10000"
            >
            <div class="parameter-description">默认值: 3,000</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              密集化梯度阈值
              <i class="fas fa-question-circle parameter-help" title="Limit that decides if points should be densified based on 2D position gradient"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.densify_grad_threshold"
                min="0.00001"
                max="0.001"
                step="0.00001"
              >
              <span class="range-value ms-2">{{ trainingParams.densify_grad_threshold }}</span>
            </div>
            <div class="parameter-description">默认值: 0.0002</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              密集化百分比
              <i class="fas fa-question-circle parameter-help" title="Percentage of scene extent a point must exceed to be forcibly densified"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.percent_dense"
                min="0.001"
                max="0.1"
                step="0.001"
              >
              <span class="range-value ms-2">{{ trainingParams.percent_dense }}</span>
            </div>
            <div class="parameter-description">默认值: 0.01</div>
          </div>
        </div>
      </div>

      <!-- 其他参数 -->
      <div class="parameter-group">
        <h6 class="mb-3">其他参数</h6>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Lambda DSSIM
              <i class="fas fa-question-circle parameter-help" title="Influence of SSIM on total loss from 0 to 1"></i>
            </div>
            <div class="d-flex align-items-center">
              <input
                type="range"
                class="form-range"
                v-model.number="trainingParams.lambda_dssim"
                min="0"
                max="1"
                step="0.01"
              >
              <span class="range-value ms-2">{{ trainingParams.lambda_dssim }}</span>
            </div>
            <div class="parameter-description">默认值 0.2</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              测试迭代
              <i class="fas fa-question-circle parameter-help" title="Iterations at which to compute L1 and PSNR over test set"></i>
            </div>
            <input
              type="text"
              class="form-control"
              v-model="testIterationsInput"
              placeholder="e.g., 7000 30000"
            >
            <div class="parameter-description">默认值: 7000 30000</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              保存迭代次数
              <i class="fas fa-question-circle parameter-help" title="Iterations at which to save the Gaussian model"></i>
            </div>
            <input
              type="text"
              class="form-control"
              v-model="saveIterationsInput"
              placeholder="e.g., 7000 30000"
            >
            <div class="parameter-description">默认值: 7000 30000</div> 
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              检查点迭代次数
              <i class="fas fa-question-circle parameter-help" title="Iterations at which to store a checkpoint for continuing later"></i>
            </div>
            <input
              type="text"
              class="form-control"
              v-model="checkpointIterationsInput"
              placeholder="e.g., 5000 15000 25000"
            >
            <div class="parameter-description">可选，空格分隔的值</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" v-model="trainingParams.quiet" id="quietOption">
              <label class="form-check-label" for="quietOption">
                安静模式
              </label>
            </div>
            <div class="parameter-description">忽略任何写入标准输出的文本</div>
          </div>

          <div class="col-md-6">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" v-model="trainingParams.debug" id="debugOption">
              <label class="form-check-label" for="debugOption">
                调试模式
              </label>
            </div>
            <div class="parameter-description">如果遇到错误，启用调试模式</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 训练控制区域 -->
    <div class="parameter-section glass-card">
      <h5>
        <i class="fas fa-play-circle me-2"></i>
        训练控制模块
      </h5>

      <div v-if="!currentTask || !currentTask.task_id" class="training-actions">
        <button
          class="btn btn-primary btn-lg control-btn primary-btn"
          @click="startTraining"
          :disabled="!selectedFolder || isProcessing"
        >
          <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-play'"></i>
          {{ isProcessing ? '正在训练' : '开始训练' }}
        </button>

        <button
          class="btn btn-outline-secondary control-btn secondary-btn"
          @click="resetParams"
          :disabled="isProcessing"
        >
          <i class="fas fa-undo me-2"></i>
          重置默认参数
        </button>

        <button
          class="btn btn-outline-warning control-btn warning-btn"
          @click="forceReset"
          title="强制重置所有状态"
        >
          <i class="fas fa-power-off me-2"></i>
          强制重置
        </button>
      </div>

      <div v-else class="training-status">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="mb-0">训练: {{ selectedFolder }}</h5>
          <div>
            <span class="badge bg-primary ms-2">{{ currentTask.status }}</span>
          </div>
        </div>

        <div class="alert" 
            :class="{
              'alert-info': currentTask.status === 'processing' || currentTask.status === 'running',
              'alert-success': currentTask.status === 'completed',
              'alert-danger': currentTask.status === 'failed',
              'alert-warning': currentTask.status === 'cancelled'
             }"
             :style="{ fontSize: '1.05em', padding: '12px' }"
        >
          <i class="fas" :class="{
            'fa-info-circle': currentTask.status === 'processing' || currentTask.status === 'running',
            'fa-check-circle': currentTask.status === 'completed',
            'fa-exclamation-circle': currentTask.status === 'failed',
            'fa-ban': currentTask.status === 'cancelled'
          }"></i>
          {{ currentTask.message }}
        </div>

        <div v-if="currentTask.status === 'processing' || currentTask.status === 'running'" class="mt-3">
          <button class="btn btn-danger control-btn danger-btn" @click="cancelTask">
            <i class="fas fa-stop me-2"></i>  取消训练
          </button>
        </div>

        <div v-if="currentTask.status === 'completed'" class="mt-3 action-buttons">
          <button class="btn btn-success control-btn success-btn me-2" @click="viewResults">
            <i class="fas fa-eye me-2"></i> 查看结果
          </button>
          <button class="btn btn-primary control-btn primary-btn" @click="resetTaskState">
            <i class="fas fa-redo me-2"></i> 训练其他模型
          </button>
        </div>

        <div v-if="currentTask.status === 'failed'" class="mt-3">
          <div v-if="currentTask.error" class="alert alert-danger mb-3">
            <strong>错误:</strong> {{ currentTask.error }}
          </div>
          <button class="btn btn-primary control-btn primary-btn" @click="resetTaskState">
            <i class="fas fa-redo me-2"></i> 再次尝试
          </button>
        </div>
      </div>
    </div>

    <!-- 训练历史记录 -->
    <div class="parameter-section glass-card">
      <h5>
        <i class="fas fa-history me-2"></i>
        训练历史记录
      </h5>

      <div v-if="loadingResults" class="text-center py-3">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2">加载历史训练...</p>
      </div>

      <div v-else-if="results.length === 0" class="text-center py-3">
        <i class="fas fa-history fa-3x text-muted mb-3"></i>
        <p class="text-muted">没有找到历史文件夹</p>
      </div>

      <div v-else class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Folder</th>
              <th>Status</th>
              <th>Training Time</th>
              <th>Trained On</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="result in results" :key="result.task_id || result.folder_name">
              <td>{{ result.folder_name }}</td>
              <td>
                <span class="badge" :class="{
                  'bg-success': result.status === 'completed',
                  'bg-danger': result.status === 'failed',
                  'bg-warning': result.status === 'cancelled',
                  'bg-secondary': result.status === 'unknown'
                }">{{ result.status }}</span>
              </td>
              <td>{{ result.processing_time ? formatTime(result.processing_time) : 'N/A' }}</td>
              <td>{{ result.timestamp ? formatDate(result.timestamp) : (result.created_time ? formatDate(result.created_time) : 'Unknown') }}</td>
              <td>
                <el-button
                  type="danger"
                  size="small"
                  @click="confirmDeleteResult(result)"
                  :icon="icons.Delete"
                >
                  删除
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script >
import { eventBus } from '@/utils/eventBus';
import { TrainingService } from '@/services/trainingService';
import { TrainingParams } from '@/utils/trainingParams';
import { TrainingUtils } from '@/utils/trainingUtils';
import { ElNotification, ElMessage, ElMessageBox } from 'element-plus';
import { shallowRef } from 'vue';
import { Delete } from '@element-plus/icons-vue';
import wsClient from '@/utils/WebSocketClient'; 

export default {
  name: 'TrainingComponent',
  data() {
    return {
      loadingFolders: true,
      loadingResults: true,
      folders: [],
      results: [],
      selectedFolder: null,
      selectedFolderDetails: null,
      taskCheckInterval: null,
      isProcessing: false,
      httpError: null,
      
      // 添加状态监控计时器和计数器
      stateMonitorInterval: null,
      stateChangeCounter: 0,
      lastTaskStatus: null,
      lastStateChangeTime: null,
      
      // 用于处理空格分隔的迭代列表
      testIterationsInput: "7000 30000",
      saveIterationsInput: "7000 30000",
      checkpointIterationsInput: "",

      // 使用默认训练参数
      trainingParams: TrainingParams.getDefaultParams(),
      
      icons: {
        Delete: shallowRef(Delete),
      }
    };
  },
  computed: {
    username() {
      return this.$store.getters.user?.username;
    },
    currentTask() {
      // 从Vuex store获取当前训练任务状态
      return this.$store.getters.trainingCurrentTask || {
        task_id: null,
        status: 'idle', // 'idle', 'running', 'processing', 'completed', 'failed', 'cancelled'
        progress: 0,
        message: '',
        output_logs: [],
        start_time: null,
        end_time: null,
        folder_name: null,
        model_path: null,
        error: null,
      };
    },

    // 将输入字符串转换为数字数组
    parsedTestIterations() {
      return this.parseIterationString(this.testIterationsInput);
    },
    parsedSaveIterations() {
      return this.parseIterationString(this.saveIterationsInput);
    },
    parsedCheckpointIterations() {
      return this.parseIterationString(this.checkpointIterationsInput);
    }
  },
  watch: {
    username(newUsername, oldUsername) {
      if (newUsername && newUsername !== oldUsername) {
        console.log(`[TrainingComponent] Username detected: ${newUsername}. Initializing component.`);
        this.syncAndInitialize();
      }
    },
    currentTask(newTask, oldTask) {
      if (newTask && newTask.task_id && (newTask.status === 'running' || newTask.status === 'processing')) {
        if (!this.taskCheckInterval) {
          this.startTaskStatusPolling(newTask.task_id);
        }
      } else if (oldTask && oldTask.task_id && (oldTask.status === 'running' || oldTask.status === 'processing')) {
        // If task is no longer running/processing, clear interval
         if (newTask.status === 'completed' || newTask.status === 'failed' || newTask.status === 'cancelled' || !newTask.task_id) {
          this.clearTaskCheckInterval();
        }
      }
    },
    // 监听输入变化，更新参数
    testIterationsInput() {
      this.trainingParams.test_iterations = this.parsedTestIterations;
    },
    saveIterationsInput() {
      this.trainingParams.save_iterations = this.parsedSaveIterations;
    },
    checkpointIterationsInput() {
      this.trainingParams.checkpoint_iterations = this.parsedCheckpointIterations;
    },
  },
  mounted() {
    // Initial data fetch if username is already available
    if (this.username) {
      this.syncAndInitialize();
    } else {
      console.log('[TrainingComponent] Username not available on mount, waiting for it to be set in store.');
    }
    eventBus.on('point-cloud-processed', this.handlePointCloudProcessed);

    this.fetchTrainingResults();
    this.fetchPointCloudFolders();
    
    // 连接WebSocket
    const token = localStorage.getItem('token');
    if(token && !wsClient.isConnected()) {
        // 注意：这里的URL需要与您的后端SocketIO服务器地址一致
        wsClient.connect('http://localhost:5000', token);
    }
    
    // 监听文件夹更新事件
    wsClient.on('folders_updated', this.handleFoldersUpdated);
    
    // 添加训练状态更新监听
    wsClient.on('training_status_update', this.handleTrainingStatusUpdate);
    
    // 启动状态监控计时器
    this.startStateMonitor();
    eventBus.on('visualization-active', this.handleVisualizationActivity);
  },
  beforeUnmount() {
    // 清理轮询和事件监听
    this.clearTaskCheckInterval();
    eventBus.off('point-cloud-processed', this.handlePointCloudProcessed);
    eventBus.off('visualization-active', this.handleVisualizationActivity); // 添加这一行
    // 移除所有监听并断开连接
    wsClient.off('folders_updated');
    wsClient.off('training_status_update');
    if(wsClient.isConnected()) {
        wsClient.disconnect();
    }
    
    // 清理状态监控计时器
    this.clearStateMonitor();
  },
  methods: {
    async syncAndInitialize() {
      await this.syncTaskWithBackend();
      this.fetchFolders();
      this.fetchResults();
    },
    handleVisualizationActivity() {
      const task = this.currentTask;
      
      if (!task || !task.task_id || !['running', 'processing'].includes(task.status)) {
        console.warn('Inconsistent state detected: Visualization is active, but UI shows no running task. Forcing state synchronization.');
        this.syncTaskWithBackend();
      }
    },
    async syncTaskWithBackend() {
      console.log("Syncing task state with backend to prevent stale cache issues.");
      try {
        const username = this.getUsername();
        if (!username) {
            this.$store.dispatch('clearTrainingTask');
            this.isProcessing = false;
            return;
        }

        const response = await TrainingService.checkActiveTask(username);
        const activeTask = (response && response.active_tasks && response.active_tasks.length > 0) ? response.active_tasks[0] : null;

        if (activeTask && ['running', 'processing'].includes(activeTask.status)) {
            console.log(`Backend reports active task: ${activeTask.task_id} with status ${activeTask.status}`);
            const taskData = {
                task_id: activeTask.task_id,
                status: activeTask.status,
                progress: activeTask.progress || 0,
                message: activeTask.message || 'Restored active task...',
                output_logs: activeTask.output_logs || [],
                start_time: activeTask.start_time,
                folder_name: activeTask.folder_name || (activeTask.source_path ? activeTask.source_path.split('/').pop() : 'Unknown'),
            };
            this.$store.dispatch('setTrainingTask', taskData);
            this.selectedFolder = taskData.folder_name;
            this.isProcessing = true;
        } else {
            console.log("Backend reports no active tasks, or task is in a final state. Clearing local state.");
            this.$store.dispatch('clearTrainingTask');
            this.isProcessing = false;
        }
      } catch (error) {
        console.error('Failed to sync task state with backend:', error);
        this.$message.error('无法同步训练状态，将清除本地状态以避免界面卡死');
        this.$store.dispatch('clearTrainingTask');
        this.isProcessing = false;
      }
    },

    getUsername() {
      return this.username;
    },

    async fetchFolders() {
      this.loadingFolders = true;
      this.httpError = null;
      try {
        const username = this.getUsername();

        const response = await TrainingService.getPointCloudResults(username);
        this.handlePointCloudResultsResponse(response);
        return this.folders;
      } catch (error) {
        this.httpError = 'Failed to load folders. Please check backend connection.';
        this.$message.error(this.httpError);
        return [];
      } finally {
        this.loadingFolders = false;
      }
    },

    async fetchResults() {
      this.loadingResults = true;
      const username = this.getUsername();
      if (!username) {
        this.loadingResults = false;
        return;
      }
      
      TrainingService.getTrainingResults(username)
        .then(response => {
          this.results = response.results || [];
        })
        .catch(error => {
          console.error('获取训练结果失败:', error);
          ElMessage.error('无法加载训练历史记录');
          this.results = [];
        })
        .finally(() => {
          this.loadingResults = false;
        });
    },

    selectFolder(folder) {
      this.selectedFolder = folder.folder_name || folder.name;
      this.selectedFolderDetails = folder;
    },

    parseIterationString(str) {
      return TrainingParams.parseIterations(str);
    },

    resetParams() {
      this.trainingParams = TrainingParams.getDefaultParams();
      this.testIterationsInput = "7000 30000";
      this.saveIterationsInput = "7000 30000";
      this.checkpointIterationsInput = "";
      ElNotification({
        title: '操作成功',
        message: '所有训练参数已恢复默认设置',
        type: 'success',
        position: 'top-right',
        duration: 2000,
        showClose: true
      });
    },

    async startTraining() {
      const folderValidation = TrainingUtils.validateFolderSelection(this.selectedFolderDetails);
      if (!folderValidation.isValid) {
        ElNotification({
          title: '操作失败',
          message: folderValidation.error,
          type: 'error',
          position: 'top-right',
          duration: 2000,
          showClose: true
        });
        return;
      }

      this.isProcessing = true;
      this.httpError = null;
      
      // 重置状态监控计数器
      this.resetStateMonitorCounters();

      try {
        const username = this.getUsername();
        const sourcePath = this.selectedFolderDetails.output_folder;

        const paramValidation = TrainingParams.validateParams(this.trainingParams);
        if (!paramValidation.isValid) {
          ElNotification({
            title: '操作失败',
            message: '参数验证失败: ' + paramValidation.errors.join(', '),
            type: 'error',
            position: 'top-right',
            duration: 2000,
            showClose: true
          });
          this.isProcessing = false; // 终止处理
          return;
        }

        // 格式化参数
        const cleanParams = TrainingParams.formatParamsForAPI(this.trainingParams);

        // 添加WebSocket配置到参数中
        cleanParams.ip = 'localhost';
        cleanParams.port = 6009;
        
        // 构造任务数据
        const taskData = {
          username: username,
          source_path: sourcePath,
          websocket_port: 6009, 
          websocket_host: 'localhost', 
          params: cleanParams
        };

        const response = await TrainingService.startTraining(taskData);
        this.handleStartTrainingResponse(response);
      } catch (error) {
        this.httpError = `Failed to start training: ${error.message}`;
        ElNotification({
          title: '操作失败',
          message: this.httpError,
          type: 'error',
          position: 'top-right',
          duration: 2000,
          showClose: true
        });
        this.$store.dispatch('setTrainingTask', { status: 'failed', message: this.httpError, error: this.httpError });
      } finally {
        this.isProcessing = false;
      }
    },

    handleStartTrainingResponse(data) {
      if (data && data.task_id) {

        const taskData = {
          task_id: data.task_id,
          status: data.status || 'running', 
          progress: 0,
          message: data.message || 'Training started...',
          output_logs: [],
          start_time: new Date().toISOString(),
          folder_name: this.selectedFolder,
          model_path: data.model_path,
          visualization_url: data.visualization ? `http://${data.visualization.host}:${data.visualization.port}` : null,
          websocket: data.websocket || { 
            host: 'localhost',
            port: 6009
          }
        };
        this.$store.dispatch('setTrainingTask', taskData);
        ElNotification({
          title: '操作成功',
          message: '训练任务已成功启动',
          type: 'success',
          position: 'bottom-right',
          customClass: 'custom-notification',
          duration: 3000
        });
      } else {
        this.$message.error('训练失败: 服务器响应无效。');
        this.$store.dispatch('setTrainingTask', { status: 'failed', message: 'Invalid server response on start.' });
      }
    },

    startTaskStatusPolling(taskId) {
      // 如果WebSocket已连接，则注册任务监听
      if (wsClient.isConnected()) {
        wsClient.emit('register_task_updates', {
          username: this.getUsername(),
          task_id: taskId
        });
      } else {
        // 如果WebSocket未连接，回退到HTTP轮询实现
        this.fallbackToHttpPolling(taskId);
      }
    },
    
    fallbackToHttpPolling(taskId) {
      if (this.taskCheckInterval) {
        clearInterval(this.taskCheckInterval);
      }
      
      this.taskCheckInterval = setInterval(async () => {
        try {
          const response = await TrainingService.getTrainingStatus(this.getUsername(), taskId);
          this.handleTrainingStatusUpdate(response);
        } catch (error) {
          console.error('轮询任务状态时发生错误:', error);
          if (error.status === 404) {
            this.$message.error('服务器上找不到任务。停止更新。');
            this.clearTaskCheckInterval();
            this.$store.dispatch('setTrainingTask', { ...this.currentTask, status: 'failed', message: '服务器上找不到任务。' });
          }
        }
      }, 3000); // 每3秒轮询一次
    },
    
    // 修改clearTaskCheckInterval方法
    clearTaskCheckInterval() {
      if (this.taskCheckInterval) {
        clearInterval(this.taskCheckInterval);
        this.taskCheckInterval = null;
      }
      
      // 如果WebSocket已连接，则取消任务更新
      if (wsClient.isConnected() && this.currentTask && this.currentTask.task_id) {
        wsClient.emit('unregister_task_updates', {
          username: this.getUsername(),
          task_id: this.currentTask.task_id
        });
      }
    },

    async checkActiveTask() {
      // This method will check if there's an active task for the user when the component mounts.
      try {
        const username = this.getUsername();
        const response = await TrainingService.checkActiveTask(username);
        
        if (response && response.active_tasks && response.active_tasks.length > 0) {
          const activeTask = response.active_tasks[0]; // Assuming one active task per user for now    
          
          this.selectedFolder = activeTask.folder_name || (activeTask.source_path ? activeTask.source_path.split('/').pop() : 'Unknown');

          const taskData = {
            task_id: activeTask.task_id,
            status: activeTask.status,
            progress: activeTask.progress || 0,
            message: activeTask.message || 'Restored active task...',
            output_logs: activeTask.output_logs || [],
            start_time: activeTask.start_time,
            folder_name: this.selectedFolder,
            // model_path might not be available in active_tasks, depends on backend
          };
          this.$store.dispatch('setTrainingTask', taskData);
          // Polling will be started by the watcher
        } else {
          console.log('No active training tasks found for user on mount.');
           // Ensure any lingering task in Vuex is cleared if backend says no active tasks
          if (this.currentTask && this.currentTask.task_id && (this.currentTask.status === 'running' || this.currentTask.status === 'processing')) {
            this.$store.dispatch('clearTrainingTask');
      }
        }
      } catch (error) {
        console.error('Error checking for active tasks:', error.response ? error.response.data : error.message);
        this.$message.error('Failed to check for active tasks.');
      }
    },

    async cancelTask() {
      if (!this.currentTask || !this.currentTask.task_id) {
        this.$message.warn('No active task to cancel.');
        return;
      }

      this.isProcessing = true; // Indicate processing start

      try {
        const username = this.getUsername();
        const taskId = this.currentTask.task_id;
      
        // Immediately stop local polling to prevent race conditions
        this.clearTaskCheckInterval();
        
        const response = await TrainingService.cancelTraining(username, taskId);
        this.handleCancelTaskResponse(response);

      } catch (error) {
        console.error('Error cancelling task:', error.response ? error.response.data : error.message);
        this.httpError = `Failed to cancel task: ${error.response?.data?.error || error.message}`;
        this.$message.error(this.httpError);
        // Even if API call fails, update local state to reflect cancellation attempt
        const currentTaskState = this.$store.getters.trainingCurrentTask;
        this.$store.dispatch('setTrainingTask', { ...currentTaskState, status: 'failed', message: 'Cancellation failed.', error: this.httpError });
      } finally {
        this.isProcessing = false; // Indicate processing end
      }
    },
    
    handleCancelTaskResponse(data) {
      ElNotification({
        title: '任务取消',
        message: data.message || '任务取消请求已成功发送',
        type: 'info',
        position: 'top-right',
        duration: 3000,
        showClose: true,
        customClass: 'custom-notification'
      });
      
      // Update task state in Vuex to 'cancelled'
      // The backend should eventually confirm this state via polling if cancellation is async
      // Or, if backend confirms immediately, this is fine.
      const currentTaskState = this.$store.getters.trainingCurrentTask;
      this.$store.dispatch('setTrainingTask', { 
        ...currentTaskState, 
        status: 'cancelled', 
        message: data.message || 'Task cancelled by user.',
        end_time: new Date().toISOString()
      });

      this.isProcessing = false; // Reset processing flag
      this.clearTaskCheckInterval(); // Ensure polling stops
      
      // Delay reset to allow user to see status, then refresh results
      setTimeout(() => {
        this.resetTaskState(); 
        this.fetchResults();
        this.fetchFolders(); // Refresh folders as well
      }, 1500);
    },

    resetTaskState() {
      this.$store.dispatch('clearTrainingTask'); // Clears the task from Vuex
      this.selectedFolder = null;
      this.selectedFolderDetails = null;
      this.isProcessing = false;
      this.httpError = null;
      this.clearTaskCheckInterval(); // Ensure polling stops
      this.$message.info('准备开始新的训练任务。');
    },

    checkAndCleanInvalidState() {
      const task = this.$store.getters.trainingCurrentTask;
      
      // 状态一致性检查 - 如果没有任务但isProcessing为true，重置它
      if ((!task || !task.task_id) && this.isProcessing) {
        console.warn('检测到无效状态：isProcessing=true但没有训练任务');
        this.isProcessing = false;
      }
      
      if (task && task.task_id && (task.status === 'running' || task.status === 'processing')) {
        // 这里应该显示任务ID
        this.verifyTaskStatusWithBackend(task.task_id);
      } else if (task && (task.status === 'cancelled' || task.status === 'failed' || task.status === 'completed')) {
        this.resetTaskState();
      }
    },

    async verifyTaskStatusWithBackend(taskId) {
      try {
        const username = this.getUsername();
        const backendTaskStatus = await TrainingService.getTrainingStatus(username, taskId);

        if (backendTaskStatus && (backendTaskStatus.status === 'running' || backendTaskStatus.status === 'processing')) {
          this.$store.dispatch('setTrainingTask', { ...this.currentTask, ...backendTaskStatus });
          // Polling will be started/managed by the watcher
        } else {
          console.log(`Task ${taskId} is not active on backend (status: ${backendTaskStatus?.status}). Clearing from store.`);
          this.$store.dispatch('clearTrainingTask');
        }
      } catch (error) {
        console.error(`Error verifying task ${taskId} with backend:`, error.response ? error.response.data : error.message);
        if (error.response && error.response.status === 404) {
           console.log(`Task ${taskId} not found on backend. Clearing from store.`);
           this.$store.dispatch('clearTrainingTask');
        }
      }
    },

    forceReset() {

      this.clearTaskCheckInterval();
      this.resetTaskState(); // This now clears Vuex and resets local component state
      ElNotification({
          title: '操作成功',
          message: '所有训练状态已重置',
          type: 'success',
          position: 'top-right',
          customClass: 'custom-notification',
          duration: 2000
        });
      this.fetchFolders(); // Refresh folder list
      this.fetchResults(); // Refresh history
    },

    handlePointCloudProcessed(processedData) {

      this.fetchFolders().then(() => {
        const folder = this.folders.find(f => f.output_folder === processedData.output_folder);
        if (folder) {
          this.selectFolder(folder);
          ElNotification({
            title: '操作成功',
            message: `自动选择新处理的文件夹: ${folder.folder_name || folder.name}`,
            type: 'success',
            position: 'top-right',
            duration: 2000,
            showClose: true
          });
        }
      });
    },

    formatDate(timestamp) {
      if (!timestamp) return 'Unknown';
      const date = new Date( (typeof timestamp === 'number' && timestamp < 10000000000) ? timestamp * 1000 : timestamp);
      return date.toLocaleString();
    },

    formatTime(seconds) {
      if (seconds === null || seconds === undefined || isNaN(seconds)) return 'N/A';
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      const s = Math.floor(seconds % 60);
      return [
        h > 0 ? `${h}h` : '',
        m > 0 ? `${m}m` : '',
        s > 0 ? `${s}s` : ''
      ].filter(Boolean).join(' ') || '0s';
    },

    handlePointCloudResultsResponse(responseData) {
      const data = responseData.data || responseData;
      if (data && data.results && Array.isArray(data.results)) {
        this.folders = data.results || [];
        if (this.folders.length === 0) {
          console.warn('No completed point cloud folders found from API.');
        }
      } else {
        console.error('Invalid point cloud results structure:', data);
        this.folders = [];
        this.$message.error('Failed to parse point cloud folder list.');
      }
    },

    async confirmDeleteResult(result) {
      try {
        await ElMessageBox.confirm(
          `您确定要永久删除训练结果文件夹 "${result.folder_name}" 及其所有内容吗？此操作不可逆。`,
          '警告',
          {
            confirmButtonText: '确定删除',
            cancelButtonText: '取消',
            type: 'warning',
          }
        );
        this.deleteResult(result);
      } catch (e) {
        ElMessage.info('删除操作已取消');
      }
    },

    async deleteResult(result) {
      try {
        const folderName = result.folder_name;

        // 检查WebSocket连接
        if (!wsClient.isConnected()) {
          ElNotification({
            title: '操作失败',
            message: 'WebSocket未连接，请刷新页面重试',
            type: 'error',
            position: 'top-right',
            duration: 2000
          });
          return;
        }

        // 显示加载中状态
        ElMessage.info('正在删除文件夹，请稍候...');

        const response = await wsClient.emitWithAck('delete_training_result', {
          token: localStorage.getItem('token'),
          folder_name: folderName,
          folderType: 'models'
        }, 30000);
        console.log('删除文件夹响应:', response);
        if (response && response.status === 'success') {
          ElNotification({
            title: '操作成功',
            message: response.message || '删除请求已成功发送',
            type: 'success',
            position: 'top-right',
            duration: 2000,
            showClose: true
          });
          
          // 刷新列表
          this.fetchResults();
        } else {
          console.error('删除失败:', response);
          ElNotification({
            title: '操作失败',
            message: response.message || '删除失败',
            type: 'error',
            position: 'top-right',
            duration: 2000,
            showClose: true
          });
        }
      } catch (error) {
        console.error('删除请求异常:', error);
        ElNotification({
          title: '操作失败',
          message: error.message || '删除请求失败或超时',
          type: 'error',
          position: 'top-right',
          duration: 2000,
          showClose: true
        });
      }
    },

    async fetchPointCloudFolders() {
      try {
        const username = this.$store.getters.user?.username;
        if (!username) {
          return;
        }
        const response = await TrainingService.getPointCloudResults(username);
        if (response && Array.isArray(response.results)) {
          this.pointCloudFolders = response.results;
        } else {
          this.pointCloudFolders = [];
        }
      } catch (err) {
        this.pointCloudFolders = [];
        ElNotification({
          title: '操作失败',
          message: '无法加载已处理的点云文件夹列表。',
          type: 'error',
          position: 'top-right',
          duration: 2000,
          showClose: true
        });
      }
    },

    handleFoldersUpdated(data) {
      const currentUser = this.$store.getters.user?.username;
      if (data.username === currentUser) {
        this.fetchTrainingResults();
        this.fetchPointCloudFolders();

      }
    },

    fetchTrainingResults() {
      this.loadingResults = true;
      const username = this.getUsername();
      if (!username) {
        this.loadingResults = false;
        return;
      }
      
      TrainingService.getTrainingResults(username)
        .then(response => {
          this.results = response.results || [];
        })
        .catch(error => {
          console.error('获取训练结果失败:', error);
          ElMessage.error('无法加载训练历史记录');
          this.results = [];
        })
        .finally(() => {
          this.loadingResults = false;
        });
    },

    updateTaskStatus(updatedTask) {
        const index = this.trainingResults.findIndex(t => t.task_id === updatedTask.task_id);
        if (index !== -1) {
            // 使用Vue的响应式方式更新数组元素
            this.trainingResults.splice(index, 1, { ...this.trainingResults[index], ...updatedTask });
        } else {
            // 如果任务不在列表中，可能是新任务，则添加到列表
            this.trainingResults.unshift(updatedTask);
        }
    },

    handleTrainingStatusUpdate(data) {
      if (!data) return;
      
      // 记录状态变化
      this.recordStateChange(data.status);
        
      // 更新Vuex存储中的任务状态
      const updatedTaskData = {
        ...this.currentTask,
        ...data
      };
      this.$store.dispatch('setTrainingTask', updatedTaskData);
      if (['completed', 'failed', 'cancelled'].includes(data.status)) {
        this.clearTaskCheckInterval();
        this.isProcessing = false;
        const finalTask = {
          ...this.currentTask,
          ...data,
          end_time: data.end_time || new Date().toISOString()
        };
        this.$store.dispatch('setTrainingTask', finalTask);
        if (data.status === 'cancelled') {
          setTimeout(() => this.resetTaskState(), 1500);
        }
        this.fetchResults();
      }
    },
    
    // 添加状态监控相关方法
    startStateMonitor() {
      // 清除任何现有的监控器
      this.clearStateMonitor();
      
      // 设置初始状态
      this.lastTaskStatus = this.currentTask?.status || 'idle';
      this.lastStateChangeTime = Date.now();
      this.stateChangeCounter = 0;
      
      // 创建新的监控器 - 每10秒检查一次状态
      this.stateMonitorInterval = setInterval(() => {
        this.checkStateStability();
      }, 10000);
    },
    
    clearStateMonitor() {
      if (this.stateMonitorInterval) {
        clearInterval(this.stateMonitorInterval);
        this.stateMonitorInterval = null;
      }
    },
    
    resetStateMonitorCounters() {
      this.stateChangeCounter = 0;
      this.lastStateChangeTime = Date.now();
      this.lastTaskStatus = this.currentTask?.status || 'idle';
    },
    
    recordStateChange(newStatus) {
      if (newStatus !== this.lastTaskStatus) {
        this.lastTaskStatus = newStatus;
        this.lastStateChangeTime = Date.now();
        this.stateChangeCounter = 0;
      }
    },
    
    checkStateStability() {
      // 只有在训练过程中才进行状态稳定性检查
      if (!this.currentTask || !this.currentTask.task_id) {
        return;
      }
      
      // 如果处于"processing"或"running"状态，检查是否长时间未变化
      if (
        (this.currentTask.status === 'processing' || this.currentTask.status === 'running') && 
        this.isProcessing
      ) {
        const now = Date.now();
        const elapsedSeconds = (now - this.lastStateChangeTime) / 1000;
        
        // 增加计数器
        this.stateChangeCounter++;
        
        // 如果状态超过2分钟未变化，且至少检查了10次
        if (elapsedSeconds > 120 && this.stateChangeCounter >= 10) {
          console.warn(`训练状态 "${this.currentTask.status}" 已经 ${Math.floor(elapsedSeconds)} 秒未变化，可能卡住了`);
          
          // 弹出通知，询问用户是否要重置
          ElMessageBox.confirm(
            `训练状态似乎已经${Math.floor(elapsedSeconds)}秒未更新。可能是后端通信问题或训练过程卡住了。`,
            '训练状态可能卡住',
            {
              confirmButtonText: '重置状态',
              cancelButtonText: '继续等待',
              type: 'warning'
            }
          ).then(() => {
            // 用户选择重置
            this.forceReset();
          }).catch(() => {
            // 用户选择继续等待，重置计数器
            this.resetStateMonitorCounters();
          });
        }
        
        // 如果状态超过5分钟未变化，自动重置
        if (elapsedSeconds > 300) {
          console.error(`训练状态 "${this.currentTask.status}" 已经 ${Math.floor(elapsedSeconds)} 秒未变化，自动重置`);
          ElNotification({
            title: '状态自动重置',
            message: `训练状态已超过5分钟未更新，系统已自动重置`,
            type: 'warning',
            position: 'top-right',
            duration: 3000
          });
          this.forceReset();
        }
      }
      
      // 检查isProcessing是否卡住 - 如果没有活动任务但isProcessing为true
      if (this.isProcessing && (!this.currentTask || !this.currentTask.task_id || 
          ['completed', 'failed', 'cancelled'].includes(this.currentTask.status))) {
        console.warn('检测到处理状态不一致：isProcessing=true但没有活动任务');
        // 重置处理状态
        this.isProcessing = false;
      }
    },
  }
};
</script>

<style src="../assets/styles/trainingComponent.css" scoped>

</style>

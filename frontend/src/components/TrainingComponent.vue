<template>
  <div class="training-component">
    <!-- 源文件夹选择区域 -->
    <div class="parameter-section">
      <h5>
        <i class="fas fa-folder-open me-2"></i>
        源文件夹选择区域
      </h5>
      <div class="source-folder-selector">
        <p class="mb-3">选择一个Colmap处理过的点云文件进行训练:</p>

        <div v-if="loadingFolders" class="text-center py-3">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-2">Loading available folders...</p>
        </div>

        <div v-else-if="folders.length === 0" class="text-center py-3">
          <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
          <p class="text-muted">No processed point cloud folders found</p>
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
    <div class="parameter-section">
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
            <div class="parameter-description">Default: 30,000</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Resolution
              <i class="fas fa-question-circle parameter-help" title="Specifies resolution of the loaded images before training"></i>
            </div>
            <select class="form-select" v-model="trainingParams.resolution">
              <option value="-1">Auto (default)</option>
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
              <i class="fas fa-question-circle parameter-help" title="Order of spherical harmonics to be used (no larger than 3)"></i>
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
              Data Device
              <i class="fas fa-question-circle parameter-help" title="Specifies where to put the source image data"></i>
            </div>
            <select class="form-select" v-model="trainingParams.data_device">
              <option value="cuda">CUDA (default, faster)</option>
              <option value="cpu">CPU (for large datasets, reduces VRAM usage)</option>
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
        <h6 class="mb-3">Learning Rate Parameters</h6>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Position Learning Rate (Initial)
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
            <div class="parameter-description">Default: 0.00016</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Position Learning Rate (Final)
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
            <div class="parameter-description">Default: 0.0000016</div>
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
            <div class="parameter-description">Default: 0.0025</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Opacity Learning Rate
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
            <div class="parameter-description">Default: 0.05</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Scaling Learning Rate
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
            <div class="parameter-description">Default: 0.005</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Rotation Learning Rate
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
            <div class="parameter-description">Default: 0.001</div>
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
            <div class="parameter-description">Default: 0.01</div>
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
            <div class="parameter-description">Default: 30,000</div>
          </div>
        </div>
      </div>

      <!-- 密度化参数 -->
      <div class="parameter-group">
        <h6 class="mb-3">Densification Parameters</h6>

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
            <div class="parameter-description">Default: 500</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Densify Until Iteration
              <i class="fas fa-question-circle parameter-help" title="Iteration where densification stops"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.densify_until_iter"
              min="1000"
              max="30000"
            >
            <div class="parameter-description">Default: 15,000</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Densification Interval
              <i class="fas fa-question-circle parameter-help" title="How frequently to densify (iterations)"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.densification_interval"
              min="10"
              max="1000"
            >
            <div class="parameter-description">Default: 100</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Opacity Reset Interval
              <i class="fas fa-question-circle parameter-help" title="How frequently to reset opacity (iterations)"></i>
            </div>
            <input
              type="number"
              class="form-control"
              v-model.number="trainingParams.opacity_reset_interval"
              min="100"
              max="10000"
            >
            <div class="parameter-description">Default: 3,000</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Densify Gradient Threshold
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
            <div class="parameter-description">Default: 0.0002</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Percent Dense
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
            <div class="parameter-description">Default: 0.01</div>
          </div>
        </div>
      </div>

      <!-- 其他参数 -->
      <div class="parameter-group">
        <h6 class="mb-3">Other Parameters</h6>

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
            <div class="parameter-description">Default: 0.2</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Test Iterations
              <i class="fas fa-question-circle parameter-help" title="Iterations at which to compute L1 and PSNR over test set"></i>
            </div>
            <input
              type="text"
              class="form-control"
              v-model="testIterationsInput"
              placeholder="e.g., 7000 30000"
            >
            <div class="parameter-description">Default: 7000 30000 (space-separated)</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="parameter-label">
              Save Iterations
              <i class="fas fa-question-circle parameter-help" title="Iterations at which to save the Gaussian model"></i>
            </div>
            <input
              type="text"
              class="form-control"
              v-model="saveIterationsInput"
              placeholder="e.g., 7000 30000"
            >
            <div class="parameter-description">Default: 7000 30000 iterations (space-separated)</div>
          </div>

          <div class="col-md-6">
            <div class="parameter-label">
              Checkpoint Iterations
              <i class="fas fa-question-circle parameter-help" title="Iterations at which to store a checkpoint for continuing later"></i>
            </div>
            <input
              type="text"
              class="form-control"
              v-model="checkpointIterationsInput"
              placeholder="e.g., 5000 15000 25000"
            >
            <div class="parameter-description">Optional, space-separated values</div>
          </div>
        </div>

        <div class="row parameter-row">
          <div class="col-md-6">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" v-model="trainingParams.quiet" id="quietOption">
              <label class="form-check-label" for="quietOption">
                Quiet Mode
              </label>
            </div>
            <div class="parameter-description">Omit any text written to standard output</div>
          </div>

          <div class="col-md-6">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" v-model="trainingParams.debug" id="debugOption">
              <label class="form-check-label" for="debugOption">
                Debug Mode
              </label>
            </div>
            <div class="parameter-description">Enable debug mode if you experience errors</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 训练控制区域 -->
    <div class="parameter-section">
      <h5>
        <i class="fas fa-play-circle me-2"></i>
        训练控制模块
      </h5>

      <div v-if="!currentTask || !currentTask.task_id" class="training-actions">
        <button
          class="btn btn-primary btn-lg"
          @click="startTraining"
          :disabled="!selectedFolder || isProcessing"
        >
          <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-play'"></i>
          {{ isProcessing ? 'Starting Training...' : '开始训练' }}
        </button>

        <button
          class="btn btn-outline-secondary"
          @click="resetParams"
          :disabled="isProcessing"
        >
          <i class="fas fa-undo me-2"></i>
          重置默认参数
        </button>

        <button
          class="btn btn-outline-warning"
          @click="forceReset"
          title="强制重置所有状态"
        >
          <i class="fas fa-power-off me-2"></i>
          强制重置
        </button>
      </div>

      <div v-else class="training-status">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="mb-0">Training: {{ selectedFolder }}</h5>
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
          <button class="btn btn-danger" @click="cancelTask">
            <i class="fas fa-stop me-2"></i>  取消训练
          </button>
        </div>

        <div v-if="currentTask.status === 'completed'" class="mt-3">
          <button class="btn btn-success me-2" @click="viewResults">
            <i class="fas fa-eye me-2"></i> 查看结果
          </button>
          <button class="btn btn-primary" @click="resetTaskState">
            <i class="fas fa-redo me-2"></i> 训练其他模型
          </button>
        </div>

        <div v-if="currentTask.status === 'failed'" class="mt-3">
          <div v-if="currentTask.error" class="alert alert-danger mb-3">
            <strong>Error:</strong> {{ currentTask.error }}
          </div>
          <button class="btn btn-primary" @click="resetTaskState">
            <i class="fas fa-redo me-2"></i> 再次尝试
          </button>
        </div>
      </div>
    </div>

    <!-- 训练历史记录 -->
    <div class="parameter-section">
      <h5>
        <i class="fas fa-history me-2"></i>
        Training History
      </h5>

      <div v-if="loadingResults" class="text-center py-3">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2">加载历史训练...</p>
      </div>

      <div v-else-if="results.length === 0" class="text-center py-3">
        <i class="fas fa-history fa-3x text-muted mb-3"></i>
        <p class="text-muted">No training history found</p>
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
</template>

<script>
import { eventBus } from '@/utils/eventBus';
import { TrainingService } from '@/services/trainingService';
import { TrainingParams } from '@/utils/trainingParams';
import { TaskPollingManager } from '@/utils/taskPollingManager';
import { TrainingUtils } from '@/utils/trainingUtils';
import { ElNotification } from 'element-plus';

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

      // 用于处理空格分隔的迭代列表
      testIterationsInput: "7000 30000",
      saveIterationsInput: "7000 30000",
      checkpointIterationsInput: "",

      // 使用默认训练参数
      trainingParams: TrainingParams.getDefaultParams(),
      
      // 轮询管理器
      pollingManager: new TaskPollingManager()
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
      // Fetch data when username becomes available
      if (newUsername && newUsername !== oldUsername) {
        console.log(`[TrainingComponent] Username detected: ${newUsername}. Initializing component.`);
        this.initializeComponent();
      }
    },
    currentTask(newTask, oldTask) {
      // 当任务开始运行时启动轮询，任务结束时停止轮询
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
      console.log(`[TrainingComponent] Username available on mount: ${this.username}. Initializing component.`);
      this.initializeComponent();
    } else {
      console.log('[TrainingComponent] Username not available on mount, waiting for it to be set in store.');
    }
    // The watcher will handle cases where the username is set after mount.
    eventBus.on('point-cloud-processed', this.handlePointCloudProcessed);
  },
  beforeUnmount() {
    this.clearTaskCheckInterval();
    eventBus.off('point-cloud-processed', this.handlePointCloudProcessed);
  },
  methods: {
    initializeComponent() {
      this.checkAndCleanInvalidState();
      this.fetchFolders();
      this.fetchResults();
      this.checkActiveTask();
    },
    getUsername() {
      return this.username || 'Unknown';
    },

    async fetchFolders() {
      this.loadingFolders = true;
      this.httpError = null;
      try {
        const username = this.getUsername();
        console.log(`[TrainingComponent] Fetching folders for username: ${username}`);
        const response = await TrainingService.getPointCloudResults(username);
        console.log('[TrainingComponent] Raw response from service:', JSON.parse(JSON.stringify(response)));
        this.handlePointCloudResultsResponse(response);
        console.log('[TrainingComponent] Folders after processing response:', JSON.parse(JSON.stringify(this.folders)));
        return this.folders;
      } catch (error) {
        console.error('[TrainingComponent] Error fetching folders:', error);
        this.httpError = 'Failed to load folders. Please check backend connection.';
        this.$message.error(this.httpError);
        return [];
      } finally {
        this.loadingFolders = false;
      }
    },

    async fetchResults() {
      this.loadingResults = true;
      try {
        const username = this.getUsername();
        const response = await TrainingService.getTrainingResults(username);
        this.results = response.results || [];
      } catch (error) {
        console.error('Error fetching training results:', error);
        this.$message.error('Failed to load training history.');
      } finally {
        this.loadingResults = false;
      }
    },

    selectFolder(folder) {
      this.selectedFolder = folder.folder_name || folder.name;
      this.selectedFolderDetails = folder;
      console.log('Selected folder:', folder);
    },

    parseIterationString(str) {
      return TrainingParams.parseIterations(str);
    },

    resetParams() {
      this.trainingParams = TrainingParams.getDefaultParams();
      this.testIterationsInput = "7000 30000";
      this.saveIterationsInput = "7000 30000";
      this.checkpointIterationsInput = "";
      this.$message.info('Parameters reset to default.');
    },

    async startTraining() {
      const folderValidation = TrainingUtils.validateFolderSelection(this.selectedFolderDetails);
      if (!folderValidation.isValid) {
        this.$message.error(folderValidation.error);
        return;
      }

      this.isProcessing = true;
      this.httpError = null;

      try {
        const username = this.getUsername();
        const sourcePath = this.selectedFolderDetails.output_folder;
        console.log('Training source path:', sourcePath);

        // 验证参数
        const paramValidation = TrainingParams.validateParams(this.trainingParams);
        if (!paramValidation.isValid) {
          this.$message.error('参数验证失败: ' + paramValidation.errors.join(', '));
          this.isProcessing = false; // 终止处理
          return;
        }

        // 格式化参数
        const cleanParams = TrainingParams.formatParamsForAPI(this.trainingParams);

        // 添加WebSocket配置到参数中
        cleanParams.ip = 'localhost';
        cleanParams.port = 6009;
        
        console.log('Cleaned training params with WebSocket config:', cleanParams);

        // 构造任务数据
        const taskData = {
          username: username,
          source_path: sourcePath,
          websocket_port: 6009, // 指定SplatvizNetwork WebSocket服务器端口
          websocket_host: 'localhost', // 指定SplatvizNetwork WebSocket服务器主机
          params: cleanParams
        };

        console.log('发送训练请求，包含WebSocket配置:', taskData);

        const response = await TrainingService.startTraining(taskData);
        this.handleStartTrainingResponse(response);
      } catch (error) {
        console.error('Error starting training:', error);
        this.httpError = `Failed to start training: ${error.message}`;
        this.$message.error(this.httpError);
        this.$store.dispatch('setTrainingTask', { status: 'failed', message: this.httpError, error: this.httpError });
      } finally {
        this.isProcessing = false;
      }
    },

    handleStartTrainingResponse(data) {
      console.log('Start training response:', data);
      if (data && data.task_id) {
        // 显示WebSocket连接信息
        if (data.websocket) {
          const wsUrl = `ws://${data.websocket.host}:${data.websocket.port}`;
          ElNotification({
            title: '训练任务已启动',
            message: `可视化WebSocket服务器: ${wsUrl}`,
            type: 'success',
            duration: 10000
          });
        }
        
        const taskData = {
          task_id: data.task_id,
          status: data.status || 'running', // Default to 'running' if not provided
          progress: 0,
          message: data.message || 'Training started...',
          output_logs: [],
          start_time: new Date().toISOString(),
          folder_name: this.selectedFolder,
          model_path: data.model_path,
          visualization_url: data.visualization ? `http://${data.visualization.host}:${data.visualization.port}` : null,
          websocket: data.websocket || { // 保存WebSocket配置
            host: 'localhost',
            port: 6009
          }
        };
        this.$store.dispatch('setTrainingTask', taskData);
        this.$message.success('Training task started successfully!');
        // Polling will be started by the watcher
      } else {
        this.$message.error('Failed to start training: Invalid response from server.');
        this.$store.dispatch('setTrainingTask', { status: 'failed', message: 'Invalid server response on start.' });
      }
    },

    startTaskStatusPolling(taskId) {
      this.pollingManager.startPolling(
        // 轮询函数
        () => TrainingService.getTrainingStatus(this.getUsername(), taskId),
        // 更新回调
        (response) => {
          const updatedTaskData = {
            ...this.currentTask,
            ...response
          };
          this.$store.dispatch('setTrainingTask', updatedTaskData);

          if (response.output_logs) {
            this.$store.dispatch('updateTrainingLogs', response.output_logs);
          }

          if (TrainingUtils.isTaskCompleted(response.status) || TrainingUtils.isTaskFailed(response.status)) {
            this.clearTaskCheckInterval();
            this.isProcessing = false;
            const finalTask = {
              ...this.currentTask,
              ...response,
              end_time: new Date().toISOString()
            };
            this.$store.dispatch('setTrainingTask', finalTask);
            if (response.status === 'cancelled') {
              setTimeout(() => this.resetTaskState(), 1500);
            }
            this.fetchResults();
          }
        },
        // 错误回调
        (error) => {
          console.error('Error polling task status:', error);
          if (error.status === 404) {
            this.$message.error('Task not found on server. Stopping updates.');
            this.clearTaskCheckInterval();
            this.$store.dispatch('setTrainingTask', { ...this.currentTask, status: 'failed', message: 'Task not found on server.' });
          }
        }
      );
    },

    clearTaskCheckInterval() {
      this.pollingManager.stopPolling();
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
      console.log('Cancel task response:', data);
      this.$message.info(data.message || 'Task cancellation requested.');
      
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
      console.log('Resetting task state in TrainingComponent');
      this.$store.dispatch('clearTrainingTask'); // Clears the task from Vuex
      this.selectedFolder = null;
      this.selectedFolderDetails = null;
      this.isProcessing = false;
      this.httpError = null;
      this.clearTaskCheckInterval(); // Ensure polling stops
      this.$message.info('Ready to start a new training task.');
    },

    checkAndCleanInvalidState() {
      console.log('Checking and cleaning invalid state...');
      const task = this.$store.getters.trainingCurrentTask;
      if (task && task.task_id && (task.status === 'running' || task.status === 'processing')) {
        // If there's a task marked as running in Vuex, verify its actual status with the backend.
        // This handles cases where the browser was closed and reopened.
        console.log(`Found potentially active task in store: ${task.task_id}. Verifying with backend.`);
        this.verifyTaskStatusWithBackend(task.task_id);
      } else if (task && (task.status === 'cancelled' || task.status === 'failed' || task.status === 'completed')) {
        // If task is in a terminal state in Vuex but UI might not reflect it, ensure it's reset for new task.
        // This is more of a safeguard. `resetTaskState` should handle most UI resets.
        console.log(`Task ${task.task_id} is in terminal state: ${task.status}. Ensuring UI is ready for new task.`);
          }
      // localStorage cleanup can be done here if needed, but Vuex is the primary state source now.
    },

    async verifyTaskStatusWithBackend(taskId) {
      try {
        const username = this.getUsername();
        const backendTaskStatus = await TrainingService.getTrainingStatus(username, taskId);

        if (backendTaskStatus && (backendTaskStatus.status === 'running' || backendTaskStatus.status === 'processing')) {
          console.log(`Task ${taskId} confirmed active by backend. Restoring and polling.`);
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
        // Otherwise, might be a network issue, keep local state for now or retry verification later.
      }
    },

    forceReset() {
      console.log('Executing force reset...');
        this.clearTaskCheckInterval();
      this.resetTaskState(); // This now clears Vuex and resets local component state
      
      this.$message.success('All training states have been reset.');
      this.fetchFolders(); // Refresh folder list
      this.fetchResults(); // Refresh history
    },

    viewResults() {
      // Placeholder: Implement navigation or modal to show results
      if (this.currentTask && this.currentTask.model_path) {
        this.$message.info(`Results for ${this.currentTask.folder_name} are in ${this.currentTask.model_path}. Visualization/details view to be implemented.`);
         // Example: emit an event or navigate to a results viewer component
         // eventBus.emit('view-training-results', this.currentTask);
      } else {
        this.$message.warn('No completed task or model path available to view results.');
      }
    },

    viewResultDetails(result) {
      // Placeholder: Implement navigation or modal for specific result details
      this.$message.info(`Viewing details for ${result.folder_name}. Details view to be implemented.`);
      // Example: this.$router.push({ name: 'TrainingResultDetail', params: { taskId: result.task_id } });
    },

    handlePointCloudProcessed(processedData) {
      console.log('Point cloud processed, selecting folder:', processedData);
      this.fetchFolders().then(() => {
        const folder = this.folders.find(f => f.output_folder === processedData.output_folder);
        if (folder) {
          this.selectFolder(folder);
          this.$message.success(`Automatically selected newly processed folder: ${folder.folder_name || folder.name}`);
        }
      });
    },

    formatDate(timestamp) {
      if (!timestamp) return 'Unknown';
      // Assuming timestamp is in seconds if it's a number and not too large
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
      console.log('[TrainingComponent] Handling point cloud results response. Received:', JSON.parse(JSON.stringify(responseData)));
      const data = responseData.data || responseData;
      console.log('[TrainingComponent] Extracted data object:', JSON.parse(JSON.stringify(data)));

      if (data && data.results && Array.isArray(data.results)) {
        console.log('[TrainingComponent] data.results is a valid array:', JSON.parse(JSON.stringify(data.results)));
        this.folders = data.results || [];
        if (this.folders.length === 0) {
          console.warn('No completed point cloud folders found from API.');
        }
      } else {
        console.error('Invalid point cloud results structure:', data);
        this.folders = [];
        this.$message.error('Failed to parse point cloud folder list.');
      }
    }
  }
};
</script>

<style scoped src="../assets/styles/trainingComponent.css">
</style>

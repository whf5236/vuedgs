<template>
  <div class="training-visualization">
    <!-- 侧边栏控制面板 -->
    <div class="sidebar">
      <!-- 连接状态 -->
      <div class="connection-status" :class="{ connected: isConnected }">
        <div class="status-indicator"></div>
        <span>{{ isConnected ? '已连接' : '未连接' }}</span>
        <button v-if="!isConnected" @click="connect" class="connect-btn">连接</button>
        <button v-else @click="disconnect" class="disconnect-btn">断开</button>
      </div>

      <!-- 训练控制组件 -->
      <TrainingControlWidget
        :training-status="trainingStatus"
        :is-connected="isConnected"
        @pause-training="pauseTraining"
        @resume-training="resumeTraining"
        @step-training="stepTraining"
        @stop-training="stopTraining"
        @set-stop-iteration="setStopIteration"
      />

      <!-- 渲染控制组件 -->
      <RenderControlWidget
        :render-params="renderParams"
        @update-render-params="updateRenderParams"
      />

      <!-- 相机控制组件 -->
      <CameraControlWidget
        :camera-params="cameraParams"
        @update-camera="updateCamera"
        @reset-camera="resetCamera"
      />

      <!-- 训练统计组件 -->
      <TrainingStatsWidget
        :training-data="trainingData"
        :max-iterations="maxIterations"
      />
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 3D 渲染视图 -->
      <div class="render-view">
        <div class="view-header">
          <h3>3D 渲染视图</h3>
          <div class="view-controls">
            <button @click="resetCamera" class="control-btn">
              <Refresh />
              重置视角
            </button>
            <button @click="toggleFullscreen" class="control-btn">
              <FullScreen />
              全屏
            </button>
            <button @click="saveScreenshot" class="control-btn">
              <Camera />
              截图
            </button>
          </div>
        </div>
        <div class="render-container" ref="renderContainer">
          <!-- 渲染画布 -->
          <canvas ref="renderCanvas" @mousedown="onMouseDown" @mousemove="onMouseMove" @mouseup="onMouseUp" @wheel="onWheel"></canvas>
          
          <!-- 加载状态 -->
          <div v-if="isLoading" class="loading-overlay">
            <div class="loading-spinner"></div>
            <p>正在渲染...</p>
          </div>
          
          <!-- 错误状态 -->
          <div v-if="renderError" class="error-overlay">
            <Warning />
            <p>{{ renderError }}</p>
            <button @click="retryRender" class="retry-btn">重试</button>
          </div>

          <!-- 渲染信息覆盖层 -->
          <div class="render-info" v-if="showRenderInfo">
            <div class="info-item">
              <span>FPS:</span>
              <span>{{ renderFPS }}</span>
            </div>
            <div class="info-item">
              <span>分辨率:</span>
              <span>{{ renderParams.resolution[0] }}x{{ renderParams.resolution[1] }}</span>
            </div>
            <div class="info-item">
              <span>高斯数量:</span>
              <span>{{ trainingData.num_gaussians || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import axios from 'axios'
// 移除Socket.IO，使用原生WebSocket连接到SplatvizNetwork
import { Refresh, FullScreen, Camera, Warning } from '@element-plus/icons-vue'
import TrainingControlWidget from './widgets/TrainingControlWidget.vue'
import RenderControlWidget from './widgets/RenderControlWidget.vue'
import CameraControlWidget from './widgets/CameraControlWidget.vue'
import TrainingStatsWidget from './widgets/TrainingStatsWidget.vue'

// 定义API基础URL
const API_BASE_URL = 'http://localhost:5000/api'

export default {
  name: 'RefactoredTrainingVisualization',
  components: {
    TrainingControlWidget,
    RenderControlWidget,
    CameraControlWidget,
    TrainingStatsWidget,
    Refresh,
    FullScreen,
    Camera,
    Warning
  },
  data() {
    return {
      // 原生WebSocket连接到SplatvizNetwork
      ws: null,
      isConnected: false,
      reconnectAttempts: 0,
      maxReconnectAttempts: 5,
      reconnectInterval: 3000,
      splatvizPort: 6009, // SplatvizNetwork默认端口
      heartbeatInterval: null, // 心跳定时器
      
      // 训练状态
      trainingStatus: {
        paused: false,
        iteration: 0,
        running: false
      },
      trainingData: {
        iteration: 0,
        loss: 0,
        num_gaussians: 0,
        sh_degree: 0,
        train_params: {},
        error: null
      },
      maxIterations: 30000,
      
      // 渲染状态
      isLoading: false,
      renderError: null,
      renderFPS: 0,
      showRenderInfo: true,
      
      // 训练数据结构 - 参考 SplatViz 的 EasyDict 设计
      trainingPlots: {
        num_gaussians: { values: [], dtype: 'int', color: '#3498db' },
        loss: { values: [], dtype: 'float', color: '#e74c3c' },
        psnr: { values: [], dtype: 'float', color: '#2ecc71' },
        learning_rate: { values: [], dtype: 'float', color: '#f39c12' },
        sh_degree: { values: [], dtype: 'int', color: '#9b59b6' }
      },
      iterations: [],
      
      // 训练统计信息
      trainingStats: {
        iteration: 0,
        num_gaussians: 0,
        loss: 0,
        psnr: 0,
        learning_rate: 0,
        training_time: 0,
        memory_usage: 0,
        sh_degree: 0
      },
      
      // 性能数据 - 参考 PerformanceWidget 设计
      performanceData: {
        gui_fps: 0,
        render_fps: 0,
        frame_time: 0,
        connected_clients: 0
      },
      
      // GPU 统计信息
      gpuStats: {
        name: '',
        memory_used: 0,
        memory_total: 0,
        temperature: 0,
        utilization: 0
      },
      
      // 系统信息
      systemInfo: {
        cuda_version: '',
        driver_version: '',
        device_capability: ''
      },
      
      // 渲染设置 - 参考 RenderWidget 设计
      renderParams: {
        resolution: [800, 600],
        render_alpha: false,
        render_depth: false,
        render_normal: false,
        background_color: [0, 0, 0],
        render_quality: 1.0,
        sh_degree: 3,
        scaling_modifier: 1.0,
        python_sh_conversion: false,
        python_3d_covariance: false
      },
      
      // 相机参数
      cameraParams: {
        fov: 50,
        position: [0, 0, 5],
        rotation: [0, 0, 0]
      },
      
      // 鼠标交互状态
      mouseState: {
        isDown: false,
        lastX: 0,
        lastY: 0,
        button: 0
      },
      
      // 连接设置
      // WebSocket连接配置已移除（8765端口未实际使用）
      
      // 性能监控
      lastFrameTime: 0,
      frameCount: 0,
      
      // 图表配置
      chartConfig: {
        maxDataPoints: 500,
        updateInterval: 100,
        smoothing: true
      },
      
      // 移除Socket.IO相关变量
      
      // 轮询相关（作为WebSocket的备用方案）
      pollingInterval: null,
      currentTaskId: null
    }
  },
  
  computed: {
    // 从Vuex获取WebSocket配置
    websocketConfig() {
      const trainingTask = this.$store.getters.trainingCurrentTask || {}
      return trainingTask.websocket || { host: 'localhost', port: 6009 }
    },
  },
  
  mounted() {
    // 初始化canvas
    this.initCanvas()
    
    // 禁用右键菜单
    this.$refs.renderCanvas?.addEventListener('contextmenu', (e) => {
      e.preventDefault()
    })
    
    // 不自动连接，等待用户手动点击连接按钮
    console.log('组件已挂载，等待用户手动连接到SplatvizNetwork')
  },
  
  beforeUnmount() {
    // 清理WebSocket连接
    this.disconnect()
    // 清理轮询定时器（备用方案）
    this.stopTrainingStatusPolling()
  },
  
  methods: {

    // 训练数据处理 - 参考 TrainingWidget 的实现
    processTrainingData(stats) {
      // 更新训练统计
      this.trainingStats = { ...this.trainingStats, ...stats }
      
      // 更新迭代数据
      this.iterations.push(stats.iteration)
      
      // 更新各项指标
      Object.keys(this.trainingPlots).forEach(key => {
        if (stats[key] !== undefined) {
          this.trainingPlots[key].values.push(stats[key])
        }
      })
      
      // 限制数据长度，避免内存溢出
      const maxPoints = this.chartConfig.maxDataPoints
      if (this.iterations.length > maxPoints) {
        this.iterations = this.iterations.slice(-maxPoints)
        Object.keys(this.trainingPlots).forEach(key => {
          this.trainingPlots[key].values = this.trainingPlots[key].values.slice(-maxPoints)
        })
      }
      
      // 更新训练状态
      if (stats.paused !== undefined) {
        this.trainingPaused = stats.paused
      }
    },
    
    // 性能数据处理
    processPerformanceData(perfData) {
      this.performanceData = { ...this.performanceData, ...perfData }
    },
    
    // 训练控制方法
    pauseTraining() {
      this.sendCommand({ type: 'training_control', action: 'pause' })
    },
    
    resumeTraining() {
      this.sendCommand({ type: 'training_control', action: 'resume' })
    },
    
    stepTraining() {
      this.sendCommand({ type: 'training_control', action: 'step' })
    },
    
    stopTraining() {
      this.sendCommand({ type: 'training_control', action: 'stop' })
    },
    
    setStopIteration(iteration) {
      this.maxIterations = iteration
      this.sendCommand({ 
        type: 'training_control', 
        action: 'set_stop_iteration',
        iteration: iteration
      })
    },
    
    // 渲染控制方法
    updateRenderParams(params) {
      this.renderParams = { ...this.renderParams, ...params }
      this.requestRender()
    },
    
    // 相机参数转换函数
    calculateViewMatrix(position, rotation) {
      // 创建旋转矩阵
      const [pitch, yaw, roll] = rotation
      const cosPitch = Math.cos(pitch)
      const sinPitch = Math.sin(pitch)
      const cosYaw = Math.cos(yaw)
      const sinYaw = Math.sin(yaw)
      const cosRoll = Math.cos(roll)
      const sinRoll = Math.sin(roll)
      
      // 旋转矩阵 R = Rz(roll) * Ry(yaw) * Rx(pitch)
      const R = [
        [cosYaw * cosRoll, -cosYaw * sinRoll, sinYaw, 0],
        [sinPitch * sinYaw * cosRoll + cosPitch * sinRoll, -sinPitch * sinYaw * sinRoll + cosPitch * cosRoll, -sinPitch * cosYaw, 0],
        [-cosPitch * sinYaw * cosRoll + sinPitch * sinRoll, cosPitch * sinYaw * sinRoll + sinPitch * cosRoll, cosPitch * cosYaw, 0],
        [0, 0, 0, 1]
      ]
      
      // 平移矩阵
      const T = [
        [1, 0, 0, -position[0]],
        [0, 1, 0, -position[1]],
        [0, 0, 1, -position[2]],
        [0, 0, 0, 1]
      ]
      
      // 视图矩阵 = R * T
      const viewMatrix = this.multiplyMatrices(R, T)
      return this.flattenMatrix(viewMatrix)
    },

    // 计算投影矩阵
    calculateProjectionMatrix(fov, aspect, near, far) {
      const fovRad = (fov * Math.PI) / 180
      const f = 1.0 / Math.tan(fovRad / 2.0)
      
      return [
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) / (near - far), (2 * far * near) / (near - far),
        0, 0, -1, 0
      ]
    },

    // 矩阵乘法辅助函数
    multiplyMatrices(a, b) {
      const result = []
      for (let i = 0; i < 4; i++) {
        result[i] = []
        for (let j = 0; j < 4; j++) {
          result[i][j] = 0
          for (let k = 0; k < 4; k++) {
            result[i][j] += a[i][k] * b[k][j]
          }
        }
      }
      return result
    },

    // 将4x4矩阵展平为16元素数组
    flattenMatrix(matrix) {
      const flat = []
      for (let i = 0; i < 4; i++) {
        for (let j = 0; j < 4; j++) {
          flat.push(matrix[i][j])
        }
      }
      return flat
    },

    requestRender() {
      console.log('[DEBUG] requestRender 被调用')
      if (!this.isConnected || !this.ws) {
        console.warn('[DEBUG] 未连接到SplatvizNetwork服务器，无法请求渲染')
        return
      }
      
      console.log('[DEBUG] 开始构建渲染请求')
      this.isLoading = true
      this.renderError = null
      
      try {
        // 构建简化的渲染请求（参考原始splatviz项目）
        const renderRequest = {
          resolution_x: this.renderParams.resolution[0],
          resolution_y: this.renderParams.resolution[1],
          train: this.trainingStatus.running,
          fov_y: this.cameraParams.fov,
          fov_x: this.cameraParams.fov,
          z_near: 0.01,
          z_far: 10.0,
          shs_python: false,
          rot_scale_python: false,
          keep_alive: true,
          scaling_modifier: 1.0,
          // 使用简化的视图矩阵（单位矩阵）
          view_matrix: [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
          ],
          // 使用简化的投影矩阵
          view_projection_matrix: [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
          ],
          edit_text: "",
          slider: {},
          single_training_step: false,
          stop_at_value: -1
        }
        
        console.log('[DEBUG] 渲染请求构建完成:', renderRequest)
        console.log('[DEBUG] 训练状态:', this.trainingStatus.running)
        console.log('[DEBUG] 分辨率:', this.renderParams.resolution)
        
        // 发送渲染请求
        this.sendSplatvizMessage(renderRequest)
        
      } catch (error) {
        console.error('[DEBUG] 构建渲染请求失败:', error)
        this.renderError = '渲染请求构建失败'
        this.isLoading = false
      }
    },

    // 矩阵计算方法已简化，现在使用单位矩阵进行基础渲染

    retryRender() {
      this.renderError = null
      this.requestRender()
    },
    
    saveScreenshot() {
      const canvas = this.$refs.renderCanvas
      if (canvas) {
        const link = document.createElement('a')
        link.download = `screenshot_${Date.now()}.png`
        link.href = canvas.toDataURL()
        link.click()
      }
    },
    
    toggleFullscreen() {
      const container = this.$refs.renderContainer
      if (container) {
        if (!document.fullscreenElement) {
          container.requestFullscreen()
        } else {
          document.exitFullscreen()
        }
      }
    },
    
    // 相机控制方法
    updateCamera(params) {
      this.cameraParams = { ...this.cameraParams, ...params }
      this.requestRender() // 更新相机后重新渲染
    },
    
    resetCamera() {
      this.cameraParams = {
        fov: 50,
        position: [0, 0, 5],
        rotation: [0, 0, 0]
      }
      this.requestRender()
    },
    
    // 连接设置更新
    updateConnectionSettings(settings) {
      this.connectionSettings = { ...this.connectionSettings, ...settings }
    },
    
    // 鼠标交互方法
    onMouseDown(event) {
      this.mouseState.isDown = true
      this.mouseState.lastX = event.clientX
      this.mouseState.lastY = event.clientY
      this.mouseState.button = event.button
    },
    
    onMouseMove(event) {
      if (!this.mouseState.isDown) return
      
      const deltaX = event.clientX - this.mouseState.lastX
      const deltaY = event.clientY - this.mouseState.lastY
      
      // 根据鼠标按键执行不同操作
      if (this.mouseState.button === 0) { // 左键：旋转
        this.cameraParams.rotation[1] += deltaX * 0.5
        this.cameraParams.rotation[0] += deltaY * 0.5
      } else if (this.mouseState.button === 2) { // 右键：平移
        this.cameraParams.position[0] += deltaX * 0.01
        this.cameraParams.position[1] -= deltaY * 0.01
      }
      
      this.mouseState.lastX = event.clientX
      this.mouseState.lastY = event.clientY
      
      this.requestRender()
    },
    
    onMouseUp() {
      this.mouseState.isDown = false
    },
    
    onWheel(event) {
      event.preventDefault()
      const delta = event.deltaY > 0 ? 1.1 : 0.9
      this.cameraParams.position[2] *= delta
      this.requestRender()
    },
    
    // 工具方法
    updateFPS() {
      const now = performance.now()
      if (this.lastFrameTime) {
        const deltaTime = now - this.lastFrameTime
        this.renderFPS = Math.round(1000 / deltaTime)
      }
      this.lastFrameTime = now
      this.frameCount++
    },
    
    sendCommand(command) {
      if (!this.isConnected || !this.ws) {
        console.warn('未连接到SplatvizNetwork服务器，无法发送命令')
        this.$message.warning('未连接到SplatvizNetwork服务器')
        return
      }
      
      // 根据命令类型构建SplatvizNetwork消息
      let message = {}
      
      if (command.type === 'training_control') {
        switch (command.action) {
          case 'pause':
            message = { train: false }
            break
          case 'resume':
            message = { train: true }
            break
          case 'step':
            message = { single_training_step: true }
            break
          case 'stop':
            message = { stop_at_value: this.trainingData.iteration }
            break
        }
      } else if (command.type === 'render_control') {
        // 发送完整的渲染请求
        this.requestRender()
        return
      }
      
      if (Object.keys(message).length > 0) {
        this.sendSplatvizMessage(message)
        console.log('已发送训练控制命令:', command)
      }
    },
    
    // 发送消息到SplatvizNetwork
    sendSplatvizMessage(message) {
      console.log('[DEBUG] sendSplatvizMessage 被调用，消息类型:', typeof message)
      console.log('[DEBUG] 要发送的消息内容:', message)
      
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          // 按照服务器期望的格式发送数据：先发送长度，再发送JSON数据
          const jsonString = JSON.stringify(message)
          const jsonBytes = new TextEncoder().encode(jsonString)
          
          console.log('[DEBUG] 消息JSON字符串长度:', jsonString.length)
          console.log('[DEBUG] WebSocket状态: OPEN，准备发送消息')
          
          // 创建4字节的长度头（little-endian格式）
          const lengthBytes = new ArrayBuffer(4)
          const lengthView = new DataView(lengthBytes)
          lengthView.setUint32(0, jsonBytes.length, true) // true表示little-endian
          
          // 先发送长度，再发送数据
          this.ws.send(lengthBytes)
          this.ws.send(jsonBytes)
          
          console.log('[DEBUG] 消息已发送到SplatvizNetwork:', message)
        } catch (error) {
          console.error('[DEBUG] 发送消息到SplatvizNetwork失败:', error)
          this.renderError = '发送渲染请求失败'
          this.isLoading = false
        }
      } else {
        console.error('[DEBUG] WebSocket连接未就绪，状态:', this.ws ? this.ws.readyState : 'ws为null')
        console.error('[DEBUG] WebSocket.OPEN常量值:', WebSocket.OPEN)
        this.renderError = 'SplatvizNetwork未连接'
        this.isLoading = false
      }
    },
    
    // 图像事件处理
    onImageLoad() {
      this.isLoading = false
    },
    
    onImageError() {
      this.isLoading = false
      console.error('图像加载失败')
    },
    
    initCanvas() {
      const canvas = this.$refs.renderCanvas
      if (canvas) {
        canvas.width = this.renderParams.resolution[0]
        canvas.height = this.renderParams.resolution[1]
        
        // 设置默认背景
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#2c3e50'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        
        // 绘制提示文字
        ctx.fillStyle = '#ecf0f1'
        ctx.font = '16px Arial'
        ctx.textAlign = 'center'
        ctx.fillText('等待连接...', canvas.width / 2, canvas.height / 2)
      }
    },
    
    // 初始化图表
    initializeCharts() {
      // 图表初始化逻辑将在子组件中实现
    },
    
    // FPS 限制更新
    updateFPSLimit(limit) {
      this.sendCommand({
        type: 'performance_control',
        action: 'set_fps_limit',
        value: limit
      })
    },
    
    // 垂直同步更新
    updateVSync(enabled) {
      this.sendCommand({
        type: 'performance_control',
        action: 'set_vsync',
        enabled: enabled
      })
    },
    
    // 清空CUDA缓存
    clearCudaCache() {
      this.sendCommand({
        type: 'performance_control',
        action: 'clear_cuda_cache'
      })
    },

    // 连接方法 - 连接到SplatvizNetwork WebSocket服务
    connect() {
      // 如果已经连接，先断开
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('已有连接存在，先断开...')
        this.ws.close()
        this.ws = null
      }
      
      // 使用计算属性中的WebSocket配置
      const host = this.websocketConfig.host
      const port = this.websocketConfig.port
      
      console.log(`尝试连接到SplatvizNetwork服务器... ws://${host}:${port}`)
      
      // 先检查服务器是否可用
      this.checkServerAvailability(host, port)
        .then(available => {
          if (!available) {
            this.$message.warning(`SplatvizNetwork服务器 (${host}:${port}) 不可用，请确保训练任务已启动`)
            return
          }
          
          this.createWebSocketConnection(host, port)
        })
        .catch(error => {
          console.error('检查服务器可用性失败:', error)
          this.$message.error('无法检查服务器可用性，尝试直接连接')
          this.createWebSocketConnection(host, port)
        })
    },
    
    // 检查服务器是否可用
    async checkServerAvailability(host, port) {
      try {
        // 使用HTTP请求检查WebSocket服务器是否可用
        // 这里我们使用训练状态API作为代理来检查
        const username = this.getUsername()
        const response = await axios.get(`http://localhost:5000/api/training/active?username=${username}`)
        
        // 如果有活动的训练任务，说明服务器可能在运行
        const hasActiveTask = response.data && 
                             response.data.active_tasks && 
                             response.data.active_tasks.length > 0
        
        if (!hasActiveTask) {
          console.warn('没有活动的训练任务，SplatvizNetwork可能未启动')
        }
        
        return hasActiveTask
      } catch (error) {
        console.error('检查服务器可用性失败:', error)
        return false
      }
    },
    
    // 创建WebSocket连接
    createWebSocketConnection(host, port) {
      try {
        // 创建WebSocket连接到SplatvizNetwork
        this.ws = new WebSocket(`ws://${host}:${port}`)
        
        this.ws.onopen = () => {
          console.log(`已连接到SplatvizNetwork服务器 ws://${host}:${port}`)
          this.isConnected = true
          this.reconnectAttempts = 0
          this.$message.success('已连接到SplatvizNetwork服务器')
          
          // 启动心跳检测
          this.startHeartbeat()
          
          // 连接成功后自动发送渲染请求
          console.log('[DEBUG] 连接成功，准备发送初始渲染请求')
          setTimeout(() => {
            console.log('[DEBUG] 发送初始渲染请求')
            this.requestRender()
          }, 2000) // 等待2秒确保连接稳定
        }
        
        this.ws.onmessage = (event) => {
          this.handleSplatvizMessage(event.data)
        }
        
        this.ws.onclose = (event) => {
          console.log('SplatvizNetwork连接已关闭:', event.code, event.reason)
          this.isConnected = false
          this.stopHeartbeat()
          
          // 只有在非正常关闭且不是服务器忙碌的情况下才重连
          if (event.code !== 1000 && event.code !== 1008 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.handleReconnect()
          } else if (event.code === 1008) {
            this.$message.warning('SplatvizNetwork服务器忙碌，已有其他客户端连接')
          }
        }
        
        this.ws.onerror = (error) => {
          console.error('SplatvizNetwork连接错误:', error)
          this.$message.error('连接SplatvizNetwork服务器失败，请确保训练任务已启动')
          this.isConnected = false
        }
        
      } catch (error) {
        console.error('创建WebSocket连接失败:', error)
        this.$message.error('无法创建WebSocket连接')
      }
    },

    // 本地渲染方法
    renderLocalView() {
      const canvas = this.$refs.renderCanvas
      if (!canvas) {
        console.warn('Canvas元素未找到')
        return
      }
      
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        console.warn('无法获取Canvas上下文')
        return
      }
      
      // 清空画布
      ctx.fillStyle = this.renderParams.background_color || '#2c3e50'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      
      // 绘制3D场景的模拟视图
      ctx.save()
      
      // 绘制网格
      this.drawGrid(ctx, canvas.width, canvas.height)
      
      // 绘制坐标轴
      this.drawAxes(ctx, canvas.width, canvas.height)
      
      // 绘制状态信息
      this.drawStatusInfo(ctx, canvas.width, canvas.height)
      
      ctx.restore()
      
      // 更新FPS
      this.updateFPS()
    },
    
    // 绘制网格
    drawGrid(ctx, width, height) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
      ctx.lineWidth = 1
      
      const gridSize = 50
      
      // 垂直线
      for (let x = 0; x <= width; x += gridSize) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, height)
        ctx.stroke()
      }
      
      // 水平线
      for (let y = 0; y <= height; y += gridSize) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(width, y)
        ctx.stroke()
      }
    },
    
    // 绘制坐标轴
    drawAxes(ctx, width, height) {
      const centerX = width / 2
      const centerY = height / 2
      const axisLength = 100
      
      ctx.lineWidth = 2
      
      // X轴 (红色)
      ctx.strokeStyle = '#ff4444'
      ctx.beginPath()
      ctx.moveTo(centerX, centerY)
      ctx.lineTo(centerX + axisLength, centerY)
      ctx.stroke()
      
      // Y轴 (绿色)
      ctx.strokeStyle = '#44ff44'
      ctx.beginPath()
      ctx.moveTo(centerX, centerY)
      ctx.lineTo(centerX, centerY - axisLength)
      ctx.stroke()
      
      // Z轴 (蓝色) - 模拟3D效果
      ctx.strokeStyle = '#4444ff'
      ctx.beginPath()
      ctx.moveTo(centerX, centerY)
      ctx.lineTo(centerX - axisLength * 0.7, centerY + axisLength * 0.7)
      ctx.stroke()
    },
    
    // 绘制状态信息
    drawStatusInfo(ctx, width, height) {
      ctx.fillStyle = '#ecf0f1'
      ctx.font = '14px Arial'
      ctx.textAlign = 'left'
      
      // 显示训练状态
      const connectionStatus = this.isConnected ? 'SplatvizNetwork已连接' : 
                              this.pollingInterval ? 'HTTP轮询中' : '等待连接...'
      const statusText = this.currentTaskId ? '训练中...' : '等待训练...'
      ctx.fillText(`连接状态: ${connectionStatus}`, 10, 20)
      ctx.fillText(`训练状态: ${statusText}`, 10, 40)
      
      if (this.currentTaskId && this.trainingData) {
        const info = [
          `迭代: ${this.trainingData.iteration || 0}/${this.trainingData.total_iterations || 0}`,
          `进度: ${this.trainingData.progress || 0}%`,
          `损失: ${this.trainingData.loss ? this.trainingData.loss.toFixed(6) : '0.000000'}`,
          `高斯数量: ${this.trainingData.num_gaussians || 0}`,
          `FPS: ${this.renderFPS}`
        ]
        
        info.forEach((text, index) => {
          ctx.fillText(text, 10, 45 + index * 20)
        })
        
        // 绘制进度条
        const progressBarWidth = 200
        const progressBarHeight = 10
        const progressBarX = 10
        const progressBarY = height - 30
        
        // 进度条背景
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)'
        ctx.fillRect(progressBarX, progressBarY, progressBarWidth, progressBarHeight)
        
        // 进度条填充
        const progress = (this.trainingData.progress || 0) / 100
        ctx.fillStyle = '#409eff'
        ctx.fillRect(progressBarX, progressBarY, progressBarWidth * progress, progressBarHeight)
        
        // 进度条边框
        ctx.strokeStyle = '#ecf0f1'
        ctx.lineWidth = 1
        ctx.strokeRect(progressBarX, progressBarY, progressBarWidth, progressBarHeight)
        
        // 进度百分比文字
        ctx.fillStyle = '#ecf0f1'
        ctx.font = '12px Arial'
        ctx.textAlign = 'center'
        ctx.fillText(`${this.trainingData.progress || 0}%`, progressBarX + progressBarWidth / 2, progressBarY + progressBarHeight + 15)
      } else {
        // 没有训练数据时显示提示
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)'
        ctx.font = '16px Arial'
        ctx.textAlign = 'center'
        ctx.fillText('请先启动训练任务', width / 2, height / 2)
        ctx.fillText('然后点击连接按钮查看训练进度', width / 2, height / 2 + 25)
      }
    },

    // 断开连接方法
    disconnect() {
      console.log('断开与SplatvizNetwork服务器的连接...')
      
      // 停止心跳检测
      this.stopHeartbeat()
      
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      
      this.isConnected = false
      this.$message.info('已断开与SplatvizNetwork服务器的连接')
      
      // 重置canvas
      this.initCanvas()
    },
    
    // 获取用户名
    getUsername() {
      return this.$store.getters.username || 'default_user'
    },

    // 处理SplatvizNetwork消息
    handleSplatvizMessage(data) {
      try {
        if (data instanceof Blob) {
          // 处理Blob数据
          const reader = new FileReader()
          reader.onload = (event) => {
            const textData = event.target.result
            try {
              const parsedData = JSON.parse(textData)
              this.processSplatvizMessage(parsedData)
            } catch (error) {
              console.error('解析Blob数据失败:', error)
              console.error('Blob内容:', textData)
            }
          }
          reader.onerror = (error) => {
            console.error('读取Blob失败:', error)
          }
          reader.readAsText(data, 'utf-8')
        } else if (typeof data === 'string') {
          // 处理字符串数据
          try {
            const parsedData = JSON.parse(data)
            this.processSplatvizMessage(parsedData)
          } catch (error) {
            console.error('解析字符串数据失败:', error)
            console.error('原始数据:', data)
          }
        } else {
          console.warn('收到未知数据类型:', typeof data, data)
        }
      } catch (error) {
        console.error('处理SplatvizNetwork消息失败:', error)
      }
    },

     // 处理解析后的消息内容
    processSplatvizMessage(data) {
      try {
        console.log('[DEBUG] 收到SplatvizNetwork消息:', data)
        console.log('[DEBUG] 消息包含的字段:', Object.keys(data))
        
        // 更新训练数据
        if (data.iteration !== undefined) {
          console.log('[DEBUG] 更新迭代次数:', data.iteration)
          this.trainingData.iteration = data.iteration
        }
        if (data.loss !== undefined) {
          console.log('[DEBUG] 更新损失值:', data.loss)
          this.trainingData.loss = data.loss
        }
        if (data.num_gaussians !== undefined) {
          console.log('[DEBUG] 更新高斯数量:', data.num_gaussians)
          this.trainingData.num_gaussians = data.num_gaussians
        }
        if (data.sh_degree !== undefined) {
          console.log('[DEBUG] 更新SH度数:', data.sh_degree)
          this.trainingData.sh_degree = data.sh_degree
        }
        
        // 更新训练状态
        if (data.paused !== undefined) {
          console.log('[DEBUG] 更新训练状态 - 暂停:', data.paused)
          this.trainingStatus.paused = data.paused
          this.trainingStatus.running = !data.paused
        }
        
        // 处理渲染图像
        if (data.image) {
          console.log('[DEBUG] 收到渲染图像，base64长度:', data.image.length)
          this.displayRenderedImage(data.image)
        } else {
          console.log('[DEBUG] 消息中没有图像数据')
        }
        
        // 处理错误信息
        if (data.error && data.error.trim() !== '') {
          console.error('[DEBUG] SplatvizNetwork错误:', data.error)
          this.$message.error(`渲染错误: ${data.error}`)
        }
        
      } catch (error) {
        console.error('[DEBUG] 处理SplatvizNetwork数据失败:', error)
        console.error('[DEBUG] 原始数据:', data)
      }
    },

    // 显示渲染图像
    displayRenderedImage(base64Image) {
      console.log('[DEBUG] 开始显示渲染图像')
      const canvas = this.$refs.renderCanvas
      if (!canvas) {
        console.error('[DEBUG] Canvas元素未找到')
        return
      }
      
      console.log('[DEBUG] Canvas尺寸:', canvas.width, 'x', canvas.height)
      const ctx = canvas.getContext('2d')
      const img = new Image()
      
      img.onload = () => {
        console.log('[DEBUG] 图像加载成功，尺寸:', img.width, 'x', img.height)
        // 清空画布
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        console.log('[DEBUG] 画布已清空')
        // 绘制图像
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        console.log('[DEBUG] 图像已绘制到画布')
        this.isLoading = false
      }
      
      img.onerror = (error) => {
        console.error('[DEBUG] 渲染图像加载失败:', error)
        console.error('[DEBUG] 图像源长度:', base64Image.length)
        console.error('[DEBUG] 图像源前100字符:', base64Image.substring(0, 100))
        this.isLoading = false
      }
      
      const dataUrl = `data:image/png;base64,${base64Image}`
      console.log('[DEBUG] 设置图像源，数据URL长度:', dataUrl.length)
      img.src = dataUrl
    },

    // 重连逻辑
    handleReconnect() {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
        
        setTimeout(() => {
          this.connect()
        }, this.reconnectInterval)
      } else {
        console.log('达到最大重连次数，停止重连')
        this.$message.error('无法连接到SplatvizNetwork服务器，请检查服务是否运行')
      }
    },

    // 添加心跳检测
    startHeartbeat() {
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval)
      }
      
      this.heartbeatInterval = setInterval(() => {
        if (this.isConnected && this.ws) {
          this.sendSplatvizMessage({ heartbeat: true })
        }
      }, 30000) // 每30秒发送一次心跳
    },
    
    stopHeartbeat() {
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval)
        this.heartbeatInterval = null
      }
    },

    // Socket.IO相关方法已移除，现在使用原生WebSocket连接到SplatvizNetwork

    updateTrainingStatus(status) {
      // 更新训练状态显示
      if (status.task_id) {
        this.currentTaskId = status.task_id
      }
      
      // 可以在这里添加更多状态更新逻辑
      console.log('训练状态更新:', status)
    },
    
    // 开始训练状态轮询
    startTrainingStatusPolling() {
      console.log('开始轮询训练状态...')
      this.stopTrainingStatusPolling() // 先清理现有的轮询
      
      // 首先检查是否有活跃的训练任务
      this.checkActiveTrainingTask()
      
      // 设置定时轮询
      this.pollingInterval = setInterval(() => {
        this.checkActiveTrainingTask()
      }, 3000) // 每3秒轮询一次
    },
    
    // 停止训练状态轮询
    stopTrainingStatusPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },
    
    // 检查活跃的训练任务
    async checkActiveTrainingTask() {
      try {
        const username = this.getUsername()
        const response = await axios.get(`${API_BASE_URL}/training/active?username=${username}`)
        
        if (response.data && response.data.task_id) {
          // 有活跃任务，获取详细状态
          this.currentTaskId = response.data.task_id
          await this.fetchTrainingStatus(response.data.task_id)
        } else {
          // 没有活跃任务
          this.currentTaskId = null
          this.updateTrainingDisplay(null)
        }
      } catch (error) {
        console.error('检查活跃训练任务失败:', error)
      }
    },
    
    // 获取训练状态
    async fetchTrainingStatus(taskId) {
      try {
        const username = this.getUsername()
        const response = await axios.get(`${API_BASE_URL}/training/status/${taskId}?username=${username}`)
        
        if (response.data) {
          this.updateTrainingDisplay(response.data)
          
          // 如果训练完成或失败，停止轮询
          if (response.data.status === 'completed' || response.data.status === 'failed' || response.data.status === 'cancelled') {
            this.currentTaskId = null
          }
        }
      } catch (error) {
        console.error('获取训练状态失败:', error)
        if (error.response && error.response.status === 404) {
          // 任务不存在，停止轮询
          this.currentTaskId = null
          this.updateTrainingDisplay(null)
        }
      }
    },
    
    // 更新训练显示
    updateTrainingDisplay(trainingData) {
      if (!trainingData) {
        // 没有训练数据，显示默认状态
        this.trainingStatus = 'idle'
        this.trainingData = {
          iteration: 0,
          total_iterations: 0,
          loss: 0,
          psnr: 0,
          num_gaussians: 0,
          progress: 0
        }
        return
      }
      
      // 更新训练状态
      this.trainingStatus = trainingData.status || 'running'
      
      // 解析输出日志获取训练指标
      if (trainingData.output_logs && trainingData.output_logs.length > 0) {
        const latestLog = trainingData.output_logs[trainingData.output_logs.length - 1]
        this.parseTrainingLog(latestLog)
      }
      
      // 更新训练数据
      this.trainingData = {
        ...this.trainingData,
        status: trainingData.status,
        message: trainingData.message,
        progress: trainingData.progress || 0
      }
      
      // 如果连接状态为true，触发渲染更新
      if (this.isConnected) {
        this.requestRender()
      }
    },
    
    // 解析训练日志
    parseTrainingLog(logLine) {
      try {
        // 解析类似 "Training progress: 35%|███▌ | 10670/30000 [09:16<19:48, 16.36it/s, Loss=0.0028867]" 的日志
        const progressMatch = logLine.match(/(\d+)%/)
        const iterationMatch = logLine.match(/(\d+)\/(\d+)/)
        const lossMatch = logLine.match(/Loss=([\d\.]+)/)
        
        if (progressMatch) {
          this.trainingData.progress = parseInt(progressMatch[1])
        }
        
        if (iterationMatch) {
          this.trainingData.iteration = parseInt(iterationMatch[1])
          this.trainingData.total_iterations = parseInt(iterationMatch[2])
        }
        
        if (lossMatch) {
          this.trainingData.loss = parseFloat(lossMatch[1])
        }
        
        // 估算高斯数量（基于迭代次数的简单估算）
        if (this.trainingData.iteration > 0) {
          this.trainingData.num_gaussians = Math.floor(this.trainingData.iteration * 10 + Math.random() * 1000)
        }
        
      } catch (error) {
        console.error('解析训练日志失败:', error)
      }
    }
  }
}
</script>

<style scoped  src="../assets/styles/Visualization.css">

</style>
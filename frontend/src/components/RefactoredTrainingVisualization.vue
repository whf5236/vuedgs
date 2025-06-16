<template>
  <div class="training-visualization-container">
    <div class="glass-card">
      <div class="card-header">
        <span>训练过程可视化</span>
      </div>

      <el-alert
        v-if="!trainingStatus || !trainingStatus.is_active"
        title="无活动训练任务"
        type="info"
        description="请先开始一个新的训练任务以启用实时可视化功能。"
        show-icon
        :closable="false"
        class="mb-4 glass-alert"
      />

      <div class="visualization-main-content" :class="{ 'disabled-overlay': !trainingStatus || !trainingStatus.is_active }">
        <div class="canvas-container" ref="canvasContainerRef">
          <canvas ref="canvasRef"></canvas>
          <div v-if="isLoading" class="loading-overlay">
            <div class="spinner"></div>
            <span>渲染中...</span>
          </div>
          <div v-if="renderError" class="error-overlay">
            <el-icon color="#F56C6C" size="24"><Warning /></el-icon>
            <p>{{ renderError }}</p>
          </div>
        </div>
        <div class="controls-panel glass-card-inner">
           <div class="status-bar">
             <span>状态:</span>
             <div class="status-indicator" :class="{ 'connected': isConnected }"></div>
             <span>{{ isConnected ? '已连接' : '未连接' }}</span>
             <el-button v-if="!isConnected" @click="handleConnect" :disabled="!trainingStatus || !trainingStatus.is_active" size="small">连接</el-button>
             <el-button v-else @click="disconnect" size="small">断开</el-button>
            </div>
           <!-- Other controls -->
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed, onUnmounted, nextTick } from 'vue';
import { useStore } from 'vuex';
import { Refresh, FullScreen, Camera, Warning } from '@element-plus/icons-vue';
import TrainingControlWidget from './widgets/TrainingControlWidget.vue';
import RenderControlWidget from './widgets/RenderControlWidget.vue';
import CameraControlWidget from './widgets/CameraControlWidget.vue';
import TrainingStatsWidget from './widgets/TrainingStatsWidget.vue';

import { useCamera } from '../composables/useCamera.js';
import { useSplatviz } from '../composables/useSplatviz.js';

import { addVectors, scaleVector, crossProduct } from '../utils/vector.js';

const props = defineProps({
  trainingStatus: {
    type: Object,
    default: () => ({ is_active: false })
  }
});

// --- Refs and State ---
const store = useStore();
const renderCanvasRef = ref(null);
const renderContainerRef = ref(null);
const canvasContainerRef = ref(null);
const canvasRef = ref(null);

// 渲染参数
const renderParams = ref({
        resolution: [800, 600],
        render_alpha: false,
        render_depth: false,
        render_normal: false,
        background_color: [0, 0, 0],
        render_quality: 1.0,
        sh_degree: 3,
        scaling_modifier: 1.0,
        python_sh_conversion: false,
    python_3d_covariance: false,
});

// 训练状态
const trainingStatus = reactive({ paused: false, iteration: 0, running: false });
const trainingData = reactive({ iteration: 0, loss: 0, num_gaussians: 0, sh_degree: 0 });
const maxIterations = ref(30000);

const showRenderInfo = ref(true);
const renderFPS = ref(0);
let lastFrameTime = 0;

// --- Composables ---
const camera = useCamera();

const onImageRendered = (imageBlob, stats) => {
    // 处理统计数据
    if (stats.iteration !== undefined) trainingData.iteration = stats.iteration;
    if (stats.loss !== undefined) trainingData.loss = stats.loss;
    if (stats.num_gaussians !== undefined) trainingData.num_gaussians = stats.num_gaussians;
    if (stats.sh_degree !== undefined) trainingData.sh_degree = stats.sh_degree;
      if (stats.paused !== undefined) {
        trainingStatus.paused = stats.paused;
        trainingStatus.running = !stats.paused;
    }
    
    // 渲染图像
    const canvas = renderCanvasRef.value;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    const url = URL.createObjectURL(imageBlob);
    img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        // 更新FPS
        const now = performance.now();
        if (lastFrameTime > 0) {
            renderFPS.value = Math.round(1000 / (now - lastFrameTime));
        }
        lastFrameTime = now;
    };
    img.src = url;
};

const {
    isConnected,
    isLoading,
    renderError,
    connect,
    disconnect,
    requestRender,
    pauseTraining,
    resumeTraining,
    stepTraining,
    stopTraining,
} = useSplatviz(camera, renderParams, trainingStatus, onImageRendered);


// --- UI Interaction State ---
const interactionState = reactive({
    isInteracting: false,
    lastRequestTime: 0,
    pendingRequest: null,
    wheelTimer: null
});

const mouseState = reactive({
    isDown: false,
    lastX: 0,
    lastY: 0,
    button: 0,
    momentum_x: 0,
    momentum_y: 0,
    momentum_factor: 0.3,
    momentum_dropoff: 0.8,
    threshold: 0.001
});

// --- Computed Properties ---
const websocketConfig = computed(() => {
    const trainingTask = store.getters.trainingCurrentTask || {};
    return trainingTask.websocket || { host: 'localhost', port: 6009 };
});

// --- Methods ---
function updateRenderParams(params) {
    renderParams.value = { ...renderParams.value, ...params };
    requestRender();
}

function updateCameraParams(params) {
    Object.assign(camera, params);
    requestRender();
}

function resetCamera() {
    camera.resetCameraToDefault();
    requestRender();
}

function setStopIteration(iteration) {
    maxIterations.value = iteration;
    stopTraining(iteration);
}

const handleConnect = () => {
    const { host, port } = websocketConfig.value;
    connect(host, port);
};

// --- Canvas and User Input ---
function throttledRequestRender() {
    const now = Date.now();
    const minInterval = interactionState.isInteracting ? 100 : 50;
    
    if (now - interactionState.lastRequestTime >= minInterval) {
        if (interactionState.pendingRequest) clearTimeout(interactionState.pendingRequest);
        requestRender('low');
        interactionState.lastRequestTime = now;
    } else {
        if (interactionState.pendingRequest) clearTimeout(interactionState.pendingRequest);
        interactionState.pendingRequest = setTimeout(() => {
            requestRender('low');
            interactionState.lastRequestTime = Date.now();
        }, minInterval - (now - interactionState.lastRequestTime));
    }
}

function applyMomentum() {
    if (mouseState.isDown) return;

    if (Math.abs(mouseState.momentum_x) > mouseState.threshold || Math.abs(mouseState.momentum_y) > mouseState.threshold) {
        camera.pose.value.yaw += mouseState.momentum_x;
        camera.pose.value.pitch += mouseState.momentum_y;
        
        mouseState.momentum_x *= mouseState.momentum_dropoff;
        mouseState.momentum_y *= mouseState.momentum_dropoff;

        camera.pose.value.pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, camera.pose.value.pitch));
        
        camera.updateCameraFromPose();
        throttledRequestRender();
        requestAnimationFrame(applyMomentum);
      } else {
        mouseState.momentum_x = 0;
        mouseState.momentum_y = 0;
    }
}


function onMouseDown(event) {
    event.preventDefault();
    mouseState.isDown = true;
    mouseState.lastX = event.clientX;
    mouseState.lastY = event.clientY;
    mouseState.button = event.button;
    interactionState.isInteracting = true;
    mouseState.momentum_x = 0;
    mouseState.momentum_y = 0;
}

function onMouseMove(event) {
    if (!mouseState.isDown) return;
    
    const deltaX = event.clientX - mouseState.lastX;
    const deltaY = event.clientY - mouseState.lastY;
    
    if (mouseState.button === 0) { // Rotate
        const xDir = camera.invert_x.value ? -1 : 1;
        const yDir = camera.invert_y.value ? -1 : 1;
        
        const new_momentum_x = xDir * deltaX * camera.rotate_speed.value * (1 - mouseState.momentum_factor);
        mouseState.momentum_x = mouseState.momentum_x * mouseState.momentum_factor + new_momentum_x;
        
        const new_momentum_y = yDir * deltaY * camera.rotate_speed.value * (1 - mouseState.momentum_factor);
        mouseState.momentum_y = mouseState.momentum_y * mouseState.momentum_factor + new_momentum_y;

        camera.pose.value.yaw += mouseState.momentum_x;
        camera.pose.value.pitch += mouseState.momentum_y;
        camera.pose.value.pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, camera.pose.value.pitch));

    } else { // Pan
        const forward = camera.forward.value;
        const up = camera.up_vector.value;
        const right = crossProduct(forward, up);
        
        const panSpeed = camera.drag_speed.value;
        const moveX = scaleVector(right, -deltaX * panSpeed);
        const moveY = scaleVector(up, deltaY * panSpeed);
        
        camera.lookat_point.value = addVectors(camera.lookat_point.value, addVectors(moveX, moveY));
    }

    mouseState.lastX = event.clientX;
    mouseState.lastY = event.clientY;
    
    camera.updateCameraFromPose();
    throttledRequestRender();
}

function onMouseUp() {
    mouseState.isDown = false;
    interactionState.isInteracting = false;
    requestRender('high');
    
    if (camera.current_control_mode.value === 'Orbit') {
       requestAnimationFrame(applyMomentum);
    }
}

function onWheel(event) {
    event.preventDefault();
    const wheel = event.deltaY > 0 ? 1 : -1;
    const mode = camera.control_modes.value[camera.current_control_mode.value];

    if (mode === 'WASD') {
        const moveDistance = camera.move_speed.value * wheel;
        const movement = scaleVector(camera.forward.value, moveDistance);
        camera.position.value = addVectors(camera.position.value, movement);
      } else {
        camera.radius.value += wheel / 10;
        camera.radius.value = Math.max(0.1, camera.radius.value);
    }
    
    camera.updateCameraFromPose();
    
    interactionState.isInteracting = true;
    if (interactionState.wheelTimer) clearTimeout(interactionState.wheelTimer);
    throttledRequestRender();
    interactionState.wheelTimer = setTimeout(() => {
        interactionState.isInteracting = false;
        requestRender('high');
    }, 150);
}

function handleKeyDown(event) {
    if (camera.control_modes.value[camera.current_control_mode.value] !== 'WASD') return;

    const speed = camera.wasd_move_speed.value;
    const forward = camera.forward.value;
    const right = crossProduct(forward, camera.up_vector.value);
    const up = camera.up_vector.value;
    let movement = [0, 0, 0];

    switch(event.key.toLowerCase()) {
        case 'w': movement = scaleVector(forward, speed); break;
        case 's': movement = scaleVector(forward, -speed); break;
        case 'a': movement = scaleVector(right, -speed); break;
        case 'd': movement = scaleVector(right, speed); break;
        case 'q': movement = scaleVector(up, -speed); break;
        case 'e': movement = scaleVector(up, speed); break;
        default: return;
    }
    
    camera.position.value = addVectors(camera.position.value, movement);
    requestRender();
    event.preventDefault();
}


// --- Lifecycle Hooks ---
onMounted(async () => {
  // Wait for the next DOM update cycle to ensure refs are available
  await nextTick();

  if (canvasRef.value) {
    // Canvas and its container should exist, set up event listeners.
    const canvas = canvasRef.value;
    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('resize', handleResize);
    window.addEventListener('keydown', handleKeyDown);

    // Initial setup
    handleResize(); 
  }

  // If there's an active training task, automatically connect
  if (props.trainingStatus && props.trainingStatus.is_active) {
    handleConnect();
  }
});

onBeforeUnmount(() => {
    disconnect();
    window.removeEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
    disconnect();
    // Clean up listeners
    if (canvasRef.value) {
        const canvas = canvasRef.value;
        canvas.removeEventListener('mousedown', onMouseDown);
        canvas.removeEventListener('mousemove', onMouseMove);
        canvas.removeEventListener('mouseup', onMouseUp);
        canvas.removeEventListener('wheel', onWheel);
    }
    window.removeEventListener('resize', handleResize);
    window.removeEventListener('keydown', handleKeyDown);
});

// Helper functions for template
const saveScreenshot = () => {
    const link = document.createElement('a');
    link.download = `screenshot_${Date.now()}.png`;
    link.href = renderCanvasRef.value.toDataURL();
    link.click();
};

const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
        renderContainerRef.value?.requestFullscreen();
      } else {
        document.exitFullscreen();
    }
};

function handleResize() {
  if (canvasContainerRef.value && canvasRef.value) {
    const container = canvasContainerRef.value;
    const canvas = canvasRef.value;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    requestRender();
  }
}
 
</script>

<style scoped>
.training-visualization-container {
  /* This root element now has no styles that would interfere with el-tabs. */
  height: 100%;
}
.glass-card {
  background: transparent;
  backdrop-filter: none;
  border-radius: 0;
  padding: 0; /* No padding on the main wrapper */
  box-sizing: border-box;
  border: none;
  color: #303133;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.glass-card-inner {
  background: rgba(0, 0, 0, 0.04); /* Subtle inner background */
  border-radius: 10px;
  padding: 15px;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1); /* Darker, subtle border */
  color: inherit;
}

.card-header {
  font-size: 1.2rem;
  font-weight: 600;
  padding-bottom: 15px;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1); /* Darker, subtle border */
  color: inherit;
}

.visualization-main-content {
  display: flex;
  gap: 20px;
  flex-grow: 1; /* Allow this to fill available space */
  min-height: 0; /* Fix flexbox overflow issue */
}
.canvas-container {
  flex-grow: 1;
  position: relative;
  background-color: #000;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.1); /* Lighter, subtle border */
}
.controls-panel {
  width: 300px;
  flex-shrink: 0;
}

.loading-overlay, .error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.7);
  color: #fff;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
}
.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #F56C6C; /* disconnected */
  transition: background-color 0.3s;
}
.status-indicator.connected {
  background-color: #67C23A; /* connected */
}

/* Re-using alert style from other components */
.glass-alert {
  background: rgba(240, 249, 255, 0.8);
  color: #333;
  border: 1px solid rgba(186, 231, 255, 0.9);
}
:deep(.glass-alert .el-alert__title) {
    color: #303133;
}
:deep(.glass-alert .el-alert__description) {
    color: #606266;
}
</style>

<template>
  <div class="training-visualization">
    <!-- 侧边栏控制面板 -->
    <div class="sidebar">
      <!-- 连接状态 -->
      <div class="connection-status" :class="{ connected: isConnected }">
        <div class="status-indicator"></div>
        <span>{{ isConnected ? '已连接' : '未连接' }}</span>
        <button v-if="!isConnected" @click="handleConnect" class="connect-btn">连接</button>
        <button v-else @click="disconnect" class="disconnect-btn">断开</button>
      </div>

      <!-- 训练控制组件 -->
      <TrainingControlWidget
        :training-status="trainingStatus"
        :is-connected="isConnected"
        @pause-training="pauseTraining"
        @resume-training="resumeTraining"
        @step-training="stepTraining"
        @stop-training="() => stopTraining(trainingData.iteration)"
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
        @update-camera="updateCameraParams"
        @reset-camera="resetCamera"
        @switch-control-mode="switchControlMode"
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
        <div class="render-container" ref="renderContainerRef">
          <!-- 渲染画布 -->
          <canvas ref="renderCanvasRef" @mousedown="onMouseDown" @mousemove="onMouseMove" @mouseup="onMouseUp" @wheel="onWheel"></canvas>
          
          <!-- 加载状态 -->
          <div v-if="isLoading" class="loading-overlay">
            <div class="loading-spinner"></div>
            <p>正在渲染...</p>
          </div>
          
          <!-- 错误状态 -->
          <div v-if="renderError" class="error-overlay">
            <Warning />
            <p>{{ renderError }}</p>
            <button @click="() => requestRender()" class="retry-btn">重试</button>
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

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue';
import { useStore } from 'vuex';
import { Refresh, FullScreen, Camera, Warning } from '@element-plus/icons-vue';
import TrainingControlWidget from './widgets/TrainingControlWidget.vue';
import RenderControlWidget from './widgets/RenderControlWidget.vue';
import CameraControlWidget from './widgets/CameraControlWidget.vue';
import TrainingStatsWidget from './widgets/TrainingStatsWidget.vue';

import { useCamera } from '../composables/useCamera.js';
import { useSplatviz } from '../composables/useSplatviz.js';

import { addVectors, scaleVector, crossProduct } from '../utils/vector.js';

// --- Refs and State ---
const store = useStore();
const renderCanvasRef = ref(null);
const renderContainerRef = ref(null);

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
onMounted(() => {
    const canvas = renderCanvasRef.value;
    if (canvas) {
        canvas.width = renderParams.value.resolution[0];
        canvas.height = renderParams.value.resolution[1];
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#2c3e50';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ecf0f1';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('等待连接...', canvas.width / 2, canvas.height / 2);
    }

    window.addEventListener('keydown', handleKeyDown);
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
});

onBeforeUnmount(() => {
    disconnect();
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
 
</script>

<style scoped src="../assets/styles/Visualization.css"></style>

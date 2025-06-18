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
          <div v-if="isLoading && !isInteracting" class="loading-overlay">
            <div class="spinner"></div>
            <span>渲染中...</span>
          </div>
          <div v-if="renderError" class="error-overlay">
            <el-icon color="#F56C6C" size="24"><Warning /></el-icon>
            <p>{{ renderError }}</p>
          </div>
        </div>

        <div class="controls-panel-container">
            <div class="controls-panel glass-card-inner">
                <div class="status-bar">
                    <span>状态:</span>
                    <div class="status-indicator" :class="{ 'connected': isConnected }"></div>
                    <span>{{ isConnected ? '已连接' : '未连接' }}</span>
                    <el-button v-if="!isConnected" @click="handleConnect" :disabled="!trainingStatus || !trainingStatus.is_active" size="small" class="ml-auto">连接</el-button>
                    <el-button v-else @click="disconnect" size="small" class="ml-auto">断开</el-button>
                </div>

                <!-- Training Controls -->
                <div class="control-section">
                    <div class="control-header">训练控制</div>
                    <div class="button-group">
                        <el-button @click="resumeTraining" :disabled="!stats.paused || !isConnected" size="small">继续</el-button>
                        <el-button @click="pauseTraining" :disabled="stats.paused || !isConnected" size="small">暂停</el-button>
                        <el-button @click="stepTraining" :disabled="!stats.paused || !isConnected" size="small">单步</el-button>
                    </div>
                    <el-input v-model="stopAtIteration" placeholder="在此迭代次数停止" size="small" class="mt-2">
                      <template #append>
                        <el-button @click="handleSetStopAt" size="small">设置</el-button>
                      </template>
                    </el-input>
                </div>
                
                <!-- Hardware Stats -->
                <div class="control-section">
                    <div class="control-header">硬件监控</div>
                    <div class="stat-item"><span>GPU:</span> <span class="stat-value">{{ stats.gpu_name }}</span></div>
                    <div class="stat-item"><span>温度:</span> <span class="stat-value">{{ stats.gpu_temperature?.toFixed(1) }} °C</span></div>
                    <div class="stat-item"><span>负载:</span> <span class="stat-value">{{ stats.gpu_load?.toFixed(1) }} %</span></div>
                    <div class="stat-item"><span>显存:</span></div>
                    <el-progress :percentage="gpuMemoryPercentage" :text-inside="true" :stroke-width="18" status="success">
                        <span>{{ stats.gpu_memory_used?.toFixed(0) }} / {{ stats.gpu_memory_total?.toFixed(0) }} MB</span>
                    </el-progress>
                </div>

                <!-- Training Stats -->
                <div class="control-section">
                    <div class="control-header">训练状态</div>
                    <div class="stat-item"><span>迭代次数:</span><span class="stat-value">{{ stats.iteration }}</span></div>
                    <div class="stat-item"><span>损失值:</span><span class="stat-value">{{ stats.loss.toFixed(7) }}</span></div>
                    <div class="stat-item"><span>高斯球:</span><span class="stat-value">{{ stats.num_gaussians }}</span></div>
                    <div class="stat-item"><span>SH阶数:</span><span class="stat-value">{{ stats.sh_degree }}</span></div>
                </div>

                <!-- Eval Console -->
                <div class="control-section eval-console">
                    <div class="control-header">实时评估</div>
                    <el-input v-model="evalCode" placeholder="例如: gs.get_opacity.mean()" size="small">
                      <template #append>
                        <el-button @click="handleSendEval" size="small">执行</el-button>
                      </template>
                    </el-input>
                    <div class="eval-result">
                        <pre>> {{ stats.eval_result || 'N/A' }}</pre>
                    </div>
                </div>
            </div>
             <!-- Chart -->
            <div class="chart-panel glass-card-inner">
                 <div class="control-header">损失函数曲线</div>
                 <div ref="lossChartRef" class="chart-container"></div>
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed, onUnmounted, nextTick, readonly } from 'vue';
import { useStore } from 'vuex';
import { Warning } from '@element-plus/icons-vue';
import { eventBus } from '@/utils/eventBus';
import { useCamera } from '../composables/useCamera.js';
import { useSplatviz } from '../composables/useSplatviz.js';
import { addVectors, scaleVector, crossProduct } from '../utils/vector.js';
import * as echarts from 'echarts';

// --- PROPS & STORE ---
const props = defineProps({
  trainingStatus: { type: Object, default: () => ({ is_active: false }) }
});
const store = useStore();

// --- REFS & STATE ---
const canvasRef = ref(null);
const lossChartRef = ref(null);
let lossChart = null;
const lossHistory = reactive([]);
const stopAtIteration = ref('');
const evalCode = ref('gs.get_opacity.mean()');

const renderParams = ref({
    resolution: [800, 600],
    python_sh_conversion: false,
    python_3d_covariance: false,
    scaling_modifier: 1.0,
});

const renderFPS = ref(0);
let lastFrameTime = 0;

// --- COMPOSABLES ---
const camera = useCamera();

// Central data handler
const onDataReceived = ({ stats, image }) => {
    if (stats) {
        // Update chart data
        if (lossHistory.length > 500) lossHistory.shift(); // Keep history bounded
        lossHistory.push([stats.iteration, stats.loss]);
        updateChart();
    }
    if (image) {
        renderImage(image);
    }
};

const {
    isConnected, isLoading, renderError, stats,
    connect, disconnect, requestRender,
    pauseTraining, resumeTraining, stepTraining, setStopAt, sendEvalCommand
} = useSplatviz(camera, renderParams, onDataReceived);

// --- INTERACTION STATE ---
const interactionState = reactive({
    isInteracting: false,
    lastRequestTime: 0,
    pendingRequest: null,
    wheelTimer: null,
    animationFrameId: null,
});
const mouseState = reactive({
    isDown: false, lastX: 0, lastY: 0, button: 0,
    momentum_x: 0, momentum_y: 0, momentum_factor: 0.3, 
    momentum_dropoff: 0.8, threshold: 0.001
});

// --- COMPUTED ---
const websocketConfig = computed(() => store.getters.trainingCurrentTask?.websocket || { host: 'localhost', port: 6009 });
const gpuMemoryPercentage = computed(() => {
    if (!stats.value.gpu_memory_total) return 0;
    return (stats.value.gpu_memory_used / stats.value.gpu_memory_total) * 100;
});

// --- METHODS ---
const handleConnect = () => {
    const { host, port } = websocketConfig.value;
    connect(host, port);
};
const handleSetStopAt = () => setStopAt(stopAtIteration.value);
const handleSendEval = () => sendEvalCommand(evalCode.value);

const renderImage = async (imageBlob) => {
    const canvas = canvasRef.value;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    try {
        const arrayBuffer = await imageBlob.arrayBuffer();
        const rgbData = new Uint8Array(arrayBuffer);
        const width = stats.value.resolution_x || 800;
        const height = stats.value.resolution_y || 600;

        if (canvas.width !== width || canvas.height !== height) {
            canvas.width = width;
            canvas.height = height;
        }

        const imageData = ctx.createImageData(width, height);
        const rgbaData = imageData.data;
        for (let i = 0, j = 0; i < rgbaData.length; i += 4, j += 3) {
            rgbaData[i] = rgbData[j]; rgbaData[i+1] = rgbData[j+1]; rgbaData[i+2] = rgbData[j+2]; rgbaData[i+3] = 255;
        }
        ctx.putImageData(imageData, 0, 0);

        const now = performance.now();
        if (lastFrameTime > 0) renderFPS.value = Math.round(1000 / (now - lastFrameTime));
        lastFrameTime = now;
        eventBus.emit('visualization-active');
    } catch (e) {
        console.error("Failed to process image data:", e);
    }
};

// --- CHART LOGIC ---
const initChart = () => {
    if (lossChartRef.value) {
        lossChart = echarts.init(lossChartRef.value);
        lossChart.setOption({
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'value', name: 'Iteration' },
            yAxis: { type: 'value', name: 'Loss', scale: true },
            series: [{ data: [], type: 'line', showSymbol: false, smooth: true }],
            grid: { left: '15%', right: '5%', top: '10%', bottom: '15%' }
        });
    }
};
const updateChart = () => {
    if (lossChart) {
        lossChart.setOption({ series: [{ data: lossHistory }] });
    }
};

// --- INTERACTION LOGIC ---
function throttledRequestRender(isPredictive = false) {
    const now = Date.now();
    const minInterval = interactionState.isInteracting ? (1000 / 60) : 50;
    if (now - interactionState.lastRequestTime < minInterval) {
        if (interactionState.pendingRequest) clearTimeout(interactionState.pendingRequest);
        interactionState.pendingRequest = setTimeout(() => throttledRequestRender(isPredictive), minInterval - (now - interactionState.lastRequestTime));
        return;
    }
    requestRender('low', isPredictive);
    interactionState.lastRequestTime = now;
}

function applyMomentum() {
    if (mouseState.isDown) { interactionState.isInteracting = false; return; }
    if (Math.abs(mouseState.momentum_x) > mouseState.threshold || Math.abs(mouseState.momentum_y) > mouseState.threshold) {
        camera.pose.value.yaw += mouseState.momentum_x;
        camera.pose.value.pitch += mouseState.momentum_y;
        mouseState.momentum_x *= mouseState.momentum_dropoff;
        mouseState.momentum_y *= mouseState.momentum_dropoff;
        camera.pose.value.pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, camera.pose.value.pitch));
        camera.updateCameraFromPose();
        throttledRequestRender(true);
        interactionState.animationFrameId = requestAnimationFrame(applyMomentum);
    } else {
        interactionState.isInteracting = false;
        requestRender('high', false);
    }
}

function onMouseDown(event) {
    event.preventDefault();
    if (interactionState.animationFrameId) cancelAnimationFrame(interactionState.animationFrameId);
    mouseState.isDown = true;
    Object.assign(mouseState, { lastX: event.clientX, lastY: event.clientY, button: event.button, momentum_x: 0, momentum_y: 0 });
    interactionState.isInteracting = true;
}

function onMouseMove(event) {
    if (!mouseState.isDown) return;
    const deltaX = event.clientX - mouseState.lastX;
    const deltaY = event.clientY - mouseState.lastY;
    if (mouseState.button === 0) { // Rotate
        const xDir = camera.invert_x.value ? -1 : 1;
        const yDir = camera.invert_y.value ? -1 : 1;
        const new_momentum_x = xDir * deltaX * camera.rotate_speed.value;
        const new_momentum_y = yDir * deltaY * camera.rotate_speed.value;
        mouseState.momentum_x = mouseState.momentum_x * mouseState.momentum_factor + new_momentum_x * (1 - mouseState.momentum_factor);
        mouseState.momentum_y = mouseState.momentum_y * mouseState.momentum_factor + new_momentum_y * (1 - mouseState.momentum_factor);
        camera.pose.value.yaw += new_momentum_x;
        camera.pose.value.pitch += new_momentum_y;
    } else { // Pan
        const panSpeed = camera.drag_speed.value;
        const moveX = scaleVector(crossProduct(camera.forward.value, camera.up_vector.value), -deltaX * panSpeed);
        const moveY = scaleVector(camera.up_vector.value, deltaY * panSpeed);
        camera.lookat_point.value = addVectors(camera.lookat_point.value, addVectors(moveX, moveY));
    }
    mouseState.lastX = event.clientX;
    mouseState.lastY = event.clientY;
    camera.updateCameraFromPose();
    throttledRequestRender(true);
}

function onMouseUp() {
    mouseState.isDown = false;
    if (camera.current_control_mode.value === 'Orbit') {
        if (Math.abs(mouseState.momentum_x) > mouseState.threshold || Math.abs(mouseState.momentum_y) > mouseState.threshold) {
            interactionState.animationFrameId = requestAnimationFrame(applyMomentum);
        } else {
            interactionState.isInteracting = false;
            requestRender('high', false);
        }
    } else {
        interactionState.isInteracting = false;
        requestRender('high', false);
    }
}

function onWheel(event) {
    event.preventDefault();
    if (interactionState.animationFrameId) cancelAnimationFrame(interactionState.animationFrameId);
    const wheel = event.deltaY > 0 ? 1 : -1;
    camera.radius.value = Math.max(0.1, camera.radius.value + wheel/10);
    camera.updateCameraFromPose();
    interactionState.isInteracting = true;
    if (interactionState.wheelTimer) clearTimeout(interactionState.wheelTimer);
    throttledRequestRender(true);
    interactionState.wheelTimer = setTimeout(() => {
        interactionState.isInteracting = false;
        requestRender('high', false);
    }, 150);
}

// --- LIFECYCLE ---
onMounted(async () => {
    await nextTick();
    if (canvasRef.value) {
        const canvas = canvasRef.value;
        canvas.addEventListener('mousedown', onMouseDown);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.addEventListener('mouseup', onMouseUp);
        canvas.addEventListener('wheel', onWheel, { passive: false });
        canvas.width = 800; canvas.height = 600;
    }
    initChart();
    if (props.trainingStatus?.is_active) handleConnect();
});

onBeforeUnmount(() => {
    disconnect();
    if (interactionState.animationFrameId) cancelAnimationFrame(interactionState.animationFrameId);
    if(lossChart) lossChart.dispose();
});

onUnmounted(() => {
    if (canvasRef.value) {
        const canvas = canvasRef.value;
        canvas.removeEventListener('mousedown', onMouseDown);
        canvas.removeEventListener('mousemove', onMouseMove);
        canvas.removeEventListener('mouseup', onMouseUp);
        canvas.removeEventListener('wheel', onWheel);
    }
});
</script>

<style scoped>
.training-visualization-container { height: 100%; }
.glass-card { background: transparent; backdrop-filter: none; border-radius: 0; padding: 0; box-sizing: border-box; border: none; color: #303133; height: 100%; display: flex; flex-direction: column; }
.glass-card-inner { background: rgba(0, 0, 0, 0.04); border-radius: 10px; padding: 15px; border: 1px solid rgba(0, 0, 0, 0.05); }
.card-header { font-size: 1.2rem; font-weight: 600; padding-bottom: 15px; margin-bottom: 15px; border-bottom: 1px solid rgba(0, 0, 0, 0.1); }
.visualization-main-content { display: flex; gap: 20px; flex-grow: 1; min-height: 0; }
.canvas-container { width: 800px; height: 100%; min-height: 600px; flex-shrink: 0; position: relative; background-color: #000; border-radius: 10px; overflow: hidden; border: 1px solid rgba(0, 0, 0, 0.1); }
.controls-panel-container { flex-grow: 1; display: flex; flex-direction: column; gap: 15px; min-width: 300px; }
.controls-panel, .chart-panel { display: flex; flex-direction: column; gap: 10px; }
.chart-panel { flex-grow: 1; min-height: 200px; }
.chart-container { width: 100%; height: 100%; flex-grow: 1; min-height: 180px;}
.loading-overlay, .error-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: rgba(0, 0, 0, 0.7); color: #fff; }
.status-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.status-indicator { width: 10px; height: 10px; border-radius: 50%; background-color: #F56C6C; transition: background-color 0.3s; }
.status-indicator.connected { background-color: #67C23A; }
.control-section { margin-bottom: 10px; }
.control-header { font-weight: 600; margin-bottom: 8px; font-size: 0.95rem; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; }
.button-group { display: flex; gap: 10px; }
.stat-item { display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; margin-bottom: 4px; }
.stat-value { font-weight: 600; color: #303133; }
.eval-result { background-color: #f5f7fa; border-radius: 4px; padding: 5px 10px; margin-top: 8px; font-family: 'Courier New', Courier, monospace; font-size: 0.85rem; word-wrap: break-word; white-space: pre-wrap; }
.eval-result pre { margin: 0; }
.ml-auto { margin-left: auto; }
.mt-2 { margin-top: 8px; }
</style>
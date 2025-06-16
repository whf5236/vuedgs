import { reactive, toRefs, watch, computed, ref } from 'vue';
import splatvizWsClient from '@/utils/SplatvizWebSocketClient'; // 导入专用的Splatviz客户端
import { multiplyMatrices, to4x4, flattenMatrix, calculateProjectionMatrix } from '../utils/matrix';
import { normalizeVector, crossProduct, subtractVectors } from '../utils/vector';

// 后端渲染服务器需要的视图矩阵计算
function createViewMatrix(position, forward, up) {
    const right = normalizeVector(crossProduct(forward, up));
    const newUp = normalizeVector(crossProduct(right, forward)); // 保证正交

    const rot = [
        [right[0], right[1], right[2], 0],
        [newUp[0], newUp[1], newUp[2], 0],
        [-forward[0], -forward[1], -forward[2], 0],
        [0, 0, 0, 1]
    ];

    const trans = [
        [1, 0, 0, -position[0]],
        [0, 1, 0, -position[1]],
        [0, 0, 1, -position[2]],
        [0, 0, 0, 1]
    ];
    
    // Libs like three.js do T*R, but others do R*T.
    // Based on original code, it seems to be R*T.
    return multiplyMatrices(rot, trans);
}


export function useSplatviz(cameraParams, renderParams, trainingStatus, onImageRendered) {
    const isConnected = ref(false); // Use a ref for state management
    const state = reactive({
        isLoading: false,
        renderError: null,
    });

    function sendSplatvizMessage(message) {
        if (!splatvizWsClient) {
            console.warn('Splatviz WebSocket client not initialized.');
            return;
        }
        splatvizWsClient.send(message);
    }
    
    // 核心渲染请求
    function requestRender(quality = 'high', isPredictive = false, view = null) {
        if (!isConnected.value) return;

        state.isLoading = !isPredictive; // 预测性渲染不显示加载动画
        state.renderError = null;

        const cam = view || cameraParams;
        const [width, height] = renderParams.value.resolution;
        const aspect = width / height;

        let actualWidth = width;
        let actualHeight = height;

        if (quality === 'low') {
            actualWidth = Math.round(width * 0.5);
            actualHeight = Math.round(height * 0.5);
        } else if (quality === 'medium') {
            actualWidth = Math.round(width * 0.75);
            actualHeight = Math.round(height * 0.75);
        }
        
        const viewMatrix = createViewMatrix(cam.position.value, cam.forward.value, cam.up_vector.value);
        const viewMatrixFlat = flattenMatrix(viewMatrix);
        
        const projMatrixFlat = calculateProjectionMatrix(cam.fov.value, aspect, 0.01, 10.0);
        const viewProjMatrix4x4 = multiplyMatrices(to4x4(projMatrixFlat), viewMatrix);

        const renderRequest = {
            resolution_x: actualWidth,
            resolution_y: actualHeight,
            train: trainingStatus.running,
            fov_y: cam.fov.value,
            z_near: 0.01,
            z_far: 10.0,
            shs_python: renderParams.value.python_sh_conversion,
            rot_scale_python: renderParams.value.python_3d_covariance,
            keep_alive: true,
            scaling_modifier: renderParams.value.scaling_modifier,
            view_matrix: viewMatrixFlat,
            view_projection_matrix: flattenMatrix(viewProjMatrix4x4),
            edit_text: "",
            slider: {},
            single_training_step: false,
            stop_at_value: -1,
            quality: quality,
            is_predictive: isPredictive
        };

        sendSplatvizMessage(renderRequest);
    }
    
    function handleMessage(message) {
        // splatvizWsClient 会自动解析JSON，我们这里假设收到的是 Blob
        const messageData = message.data; // 从包装对象中获取Blob数据
        if (messageData instanceof Blob) {
            if (state.pendingStats) {
                onImageRendered(messageData, state.pendingStats);
                if (!state.pendingStats.is_predictive) {
                    state.isLoading = false;
                }
                state.pendingStats = null;
            } else {
                console.warn("收到图像数据，但没有对应的统计信息，已忽略。");
            }
        } else {
            console.warn("收到了非Blob类型的消息，当前处理器无法处理:", messageData);
        }
    }

    function handleStatsMessage(data) {
        // 这是处理JSON统计数据的新函数
         if (data.error && data.error.trim() !== '') {
            console.error('SplatvizNetwork错误:', data.error);
            state.renderError = data.error;
            state.isLoading = false;
        } else {
            state.pendingStats = data;
        }
    }
    
    async function connect(host, port, userId) {
        if (isConnected.value) {
            console.log("WebSocket 已连接，无需重复连接。");
            requestRender(); // 如果已经连接，直接渲染
            return;
        }

        try {
            // Register callbacks BEFORE connecting
            splatvizWsClient.onOpen(() => {
                isConnected.value = true;
            });
            splatvizWsClient.onClose(() => {
                isConnected.value = false;
            });
            
            await splatvizWsClient.connect(`ws://${host}:${port}`, userId);
            
            // 注册特定于此模块的消息处理器
            // 注意: splatvizWsClient需要支持二进制(Blob)和文本(JSON)消息的区分处理
            // 我们假设 onMessage 只处理我们关心的特定类型
            splatvizWsClient.onMessage('splat_stats', handleStatsMessage); 
            splatvizWsClient.onMessage('splat_image', handleMessage); // 假设图片消息类型为'splat_image'

            console.log(`已连接到SplatvizNetwork服务器 ws://${host}:${port}`);
            requestRender(); // 初次连接成功后渲染

        } catch (error) {
            isConnected.value = false;
            state.renderError = `连接SplatvizNetwork服务器失败: ${error.message}`;
            console.error('SplatvizNetwork连接错误:', error);
        }
    }

    function disconnect() {
        if (splatvizWsClient) {
            splatvizWsClient.disconnect(); // This will trigger the onClose callback
        }
        console.log("已从 SplatvizNetwork断开连接。");
    }

    // 公开的训练控制方法
    const sendCommand = (command) => sendSplatvizMessage(command);
    const pauseTraining = () => sendCommand({ train: false });
    const resumeTraining = () => sendCommand({ train: true });
    const stepTraining = () => sendCommand({ single_training_step: true });
    const stopTraining = (iteration) => sendCommand({ stop_at_value: iteration });

    return {
        isConnected, // Return the ref directly
        ...toRefs(state),
        connect,
        disconnect,
        requestRender,
        sendCommand,
        pauseTraining,
        resumeTraining,
        stepTraining,
        stopTraining,
    };
} 
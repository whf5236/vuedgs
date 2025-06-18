import { reactive, toRefs, readonly } from 'vue';
import splatvizWsClient from '@/utils/SplatvizWebSocketClient'; // Assuming this client can differentiate binary/text messages
import { multiplyMatrices, to4x4, flattenMatrix, calculateProjectionMatrix } from '../utils/matrix';
import { normalizeVector, crossProduct } from '../utils/vector';

// A helper function from the original splatviz project, good practice
function createViewMatrix(position, forward, up) {
    const right = normalizeVector(crossProduct(forward, up));
    const newUp = normalizeVector(crossProduct(right, forward)); // Re-orthogonalize
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
    return multiplyMatrices(rot, trans);
}


export function useSplatviz(cameraParams, renderParams, onDataReceived) {
    const state = reactive({
        isConnected: false,
        isLoading: false,
        renderError: null,
        stats: {
            iteration: 0,
            loss: 0.0,
            num_gaussians: 0,
            sh_degree: 0,
            paused: true, // Assume paused at start
            gpu_name: "N/A",
            gpu_load: 0,
            gpu_memory_used: 0,
            gpu_memory_total: 1, // Avoid division by zero
            gpu_temperature: 0,
            eval_result: null,
            train_params: {}
        },
    });

    function sendCommand(message) {
        if (!state.isConnected) {
            console.warn("WebSocket not connected, cannot send command.");
            return;
        }
        splatvizWsClient.send(message);
    }
    
    // Core render request function
    function requestRender(quality = 'high', isPredictive = false) {
        if (!state.isConnected) return;

        state.isLoading = !isPredictive;
        state.renderError = null;

        const cam = cameraParams;
        const [width, height] = renderParams.value.resolution;
        const aspect = width / height;
        let [actualWidth, actualHeight] = [width, height];

        if (quality === 'low') {
            actualWidth = Math.round(width * 0.5);
            actualHeight = Math.round(height * 0.5);
        }
        
        const viewMatrix = createViewMatrix(cam.position.value, cam.forward.value, cam.up_vector.value);
        const projMatrix = calculateProjectionMatrix(cam.fov.value, aspect, 0.01, 10.0);
        const viewProjMatrix = multiplyMatrices(to4x4(projMatrix), viewMatrix);

        const renderRequest = {
            resolution_x: actualWidth,
            resolution_y: actualHeight,
            fov_y: cam.fov.value,
            fov_x: 2 * Math.atan(Math.tan(cam.fov.value / 2) * aspect),
            z_near: 0.01,
            z_far: 10.0,
            shs_python: renderParams.value.python_sh_conversion,
            rot_scale_python: renderParams.value.python_3d_covariance,
            scaling_modifier: renderParams.value.scaling_modifier,
            view_matrix: flattenMatrix(viewMatrix),
            view_projection_matrix: flattenMatrix(viewProjMatrix),
        };
        sendCommand(renderRequest);
    }
    
    function handleStatsMessage(data) {
        Object.assign(state.stats, data);
        if (data.error && data.error.trim() !== '') {
            state.renderError = data.error;
        }
        // Always pass stats up, even if there's no new image
        onDataReceived({ stats: readonly(state.stats) });
    }
    
    function handleImageMessage(blob) {
        state.isLoading = false;
        state.renderError = null;
        // Pass the image up for rendering
        onDataReceived({ image: blob });
    }

    async function connect(host, port, userId) {
        if (state.isConnected) return;
        try {
            splatvizWsClient.onOpen(() => { state.isConnected = true; });
            splatvizWsClient.onClose(() => { state.isConnected = false; });
            // Assuming client can distinguish text (stats) and binary (image)
            splatvizWsClient.onMessage('splat_stats', handleStatsMessage); 
            splatvizWsClient.onMessage('splat_image', handleImageMessage);
            
            await splatvizWsClient.connect(`ws://${host}:${port}`, userId);
            console.log(`Connected to SplatvizNetwork server ws://${host}:${port}`);
        } catch (error) {
            state.isConnected = false;
            state.renderError = `Connection failed: ${error.message}`;
        }
    }

    function disconnect() {
        if (splatvizWsClient) {
            splatvizWsClient.disconnect();
        }
    }

    // New control methods
    const pauseTraining = () => sendCommand({ command: 'pause' });
    const resumeTraining = () => sendCommand({ command: 'resume' });
    const stepTraining = () => sendCommand({ command: 'step' });
    const setStopAt = (iteration) => sendCommand({ command: 'stop_at', iteration: parseInt(iteration, 10) || -1 });
    const sendEvalCommand = (code) => sendCommand({ command: 'eval', code });

    return {
        ...toRefs(state),
        connect,
        disconnect,
        requestRender,
        // Training controls
        pauseTraining,
        resumeTraining,
        stepTraining,
        setStopAt,
        sendEvalCommand,
    };
}
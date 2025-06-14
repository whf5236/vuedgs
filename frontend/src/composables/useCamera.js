import { reactive, toRefs } from 'vue';
import { addVectors, subtractVectors, scaleVector, crossProduct, normalizeVector } from '../utils/vector';
import { rotateCoordinates } from '../utils/matrix';

// 初始相机状态
const getInitialCameraState = () => ({
  fov: 60,
  radius: 5,
  lookat_point: [0, 0, 0],
  up_vector: [0, 1, 0],
  pose: {
    yaw: Math.PI,
    pitch: 0
  },
  position: [0, 0, 5],
  rotation: [0, 0, 0], // Note: rotation is for view matrix, pose is for control
  forward: [0, 0, -1],
  control_modes: ['Orbit', 'WASD'],
  current_control_mode: 0,
  move_speed: 0.02,
  wasd_move_speed: 0.1,
  drag_speed: 0.005,
  rotate_speed: 0.002,
  invert_x: false,
  invert_y: false,
});

export function useCamera() {
  const cameraParams = reactive(getInitialCameraState());

  /**
   * 核心: 复现 Python `get_origin`
   * @param {number} h horizontal_mean (yaw)
   * @param {number} v vertical_mean (pitch)
   * @param {number} r radius
   * @param {number[]} lookat lookat_position
   * @param {number[]} up up_vector
   * @returns {number[]}
   */
  function getOrigin(h, v, r, lookat, up) {
    // 1. Clamp pitch
    const v_clamped = Math.max(1e-5, Math.min(v, Math.PI - 1e-5));
    
    // 2. 球坐标计算 (注意后端用 `math.pi - h`)
    let initial_coords = [
        r * Math.sin(v_clamped) * Math.cos(Math.PI - h),
        r * Math.cos(v_clamped),
        r * Math.sin(v_clamped) * Math.sin(Math.PI - h)
    ];

    // 3. 关键步骤: 根据 up_vector 旋转坐标
    const rotated_coords = rotateCoordinates(initial_coords, up);
    
    // 4. 添加 lookat_position
    return addVectors(rotated_coords, lookat);
  }

  /**
   * 核心: 复现 Python `get_forward_vector`
   */
  function getForwardVector(camera_origins, lookat_position) {
      return normalizeVector(subtractVectors(lookat_position, camera_origins));
  }

  function updateCameraFromPose() {
    const mode = cameraParams.control_modes[cameraParams.current_control_mode];
    
    if (mode === 'Orbit') {
      cameraParams.position = getOrigin(
        cameraParams.pose.yaw,
        cameraParams.pose.pitch,
        cameraParams.radius,
        cameraParams.lookat_point,
        cameraParams.up_vector
      );
      
      cameraParams.forward = getForwardVector(cameraParams.position, cameraParams.lookat_point);
      
    } else if (mode === 'WASD') {
        const h = cameraParams.pose.yaw + Math.PI / 2;
        const v = cameraParams.pose.pitch + Math.PI / 2;
        cameraParams.forward = normalizeVector([
            Math.sin(v) * Math.cos(h),
            Math.cos(v),
            Math.sin(v) * Math.sin(h)
        ]);
    }
  }

  function resetCameraToDefault() {
      Object.assign(cameraParams, getInitialCameraState());
      updateCameraFromPose();
  }
  
  function switchControlMode(modeIndex) {
      if (modeIndex >= 0 && modeIndex < cameraParams.control_modes.length) {
        cameraParams.current_control_mode = modeIndex;
        updateCameraFromPose();
      }
  }

  return {
    ...toRefs(cameraParams), // 导出为 refs, 方便解构
    getOrigin,
    getForwardVector,
    updateCameraFromPose,
    resetCameraToDefault,
    switchControlMode
  };
} 
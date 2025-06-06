<template>
  <div class="camera-control-widget">
    <div class="widget-header">
      <h3>相机控制</h3>
      <button @click="$emit('reset-camera')" class="reset-btn">
        重置
      </button>
    </div>
    
    <div class="widget-content">
      <!-- 视野角度 -->
      <div class="setting-group">
        <label>视野角度 (FOV)</label>
        <el-slider
          v-model="localParams.fov"
          @change="updateCamera"
          :min="10"
          :max="120"
          :step="1"
          show-input
          show-tooltip
        />
      </div>

      <!-- 相机位置 -->
      <div class="setting-group">
        <label>相机位置</label>
        <div class="vector-input">
          <div class="axis-input">
            <label>X:</label>
            <el-input-number
              v-model="localParams.position[0]"
              @change="updateCamera"
              :step="0.1"
              :precision="2"
              size="small"
            />
          </div>
          <div class="axis-input">
            <label>Y:</label>
            <el-input-number
              v-model="localParams.position[1]"
              @change="updateCamera"
              :step="0.1"
              :precision="2"
              size="small"
            />
          </div>
          <div class="axis-input">
            <label>Z:</label>
            <el-input-number
              v-model="localParams.position[2]"
              @change="updateCamera"
              :step="0.1"
              :precision="2"
              size="small"
            />
          </div>
        </div>
      </div>

      <!-- 相机旋转 -->
      <div class="setting-group">
        <label>相机旋转 (度)</label>
        <div class="vector-input">
          <div class="axis-input">
            <label>俯仰:</label>
            <el-input-number
              v-model="localParams.rotation[0]"
              @change="updateCamera"
              :min="-90"
              :max="90"
              :step="1"
              size="small"
            />
          </div>
          <div class="axis-input">
            <label>偏航:</label>
            <el-input-number
              v-model="localParams.rotation[1]"
              @change="updateCamera"
              :min="-180"
              :max="180"
              :step="1"
              size="small"
            />
          </div>
          <div class="axis-input">
            <label>翻滚:</label>
            <el-input-number
              v-model="localParams.rotation[2]"
              @change="updateCamera"
              :min="-180"
              :max="180"
              :step="1"
              size="small"
            />
          </div>
        </div>
      </div>

      <!-- 相机预设 -->
      <div class="setting-group">
        <label>相机预设</label>
        <div class="preset-grid">
          <button @click="applyPreset('front')" class="preset-btn">正面</button>
          <button @click="applyPreset('back')" class="preset-btn">背面</button>
          <button @click="applyPreset('left')" class="preset-btn">左侧</button>
          <button @click="applyPreset('right')" class="preset-btn">右侧</button>
          <button @click="applyPreset('top')" class="preset-btn">顶部</button>
          <button @click="applyPreset('bottom')" class="preset-btn">底部</button>
        </div>
      </div>

      <!-- 相机控制模式 -->
      <div class="setting-group">
        <label>控制模式</label>
        <el-radio-group v-model="controlMode" @change="updateControlMode" size="small">
          <el-radio label="orbit">轨道</el-radio>
          <el-radio label="fly">飞行</el-radio>
          <el-radio label="fps">第一人称</el-radio>
        </el-radio-group>
      </div>

      <!-- 移动速度 -->
      <div class="setting-group">
        <label>移动速度</label>
        <el-slider
          v-model="moveSpeed"
          @change="updateMoveSpeed"
          :min="0.1"
          :max="5.0"
          :step="0.1"
          :precision="1"
          show-tooltip
        />
      </div>

      <!-- 相机信息显示 -->
      <div class="setting-group">
        <label>相机信息</label>
        <div class="camera-info">
          <div class="info-item">
            <span>距离原点:</span>
            <span>{{ distance.toFixed(2) }}</span>
          </div>
          <div class="info-item">
            <span>朝向:</span>
            <span>{{ direction }}</span>
          </div>
        </div>
      </div>

      <!-- 快捷操作 -->
      <div class="setting-group">
        <label>快捷操作</label>
        <div class="quick-actions">
          <button @click="lookAtOrigin" class="action-btn">看向原点</button>
          <button @click="frameAll" class="action-btn">框选全部</button>
          <button @click="saveView" class="action-btn">保存视图</button>
          <button @click="loadView" class="action-btn" :disabled="!savedView">加载视图</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CameraControlWidget',
  props: {
    cameraParams: {
      type: Object,
      default: () => ({
        fov: 50,
        position: [0, 0, 5],
        rotation: [0, 0, 0]
      })
    }
  },
  emits: ['update-camera', 'reset-camera'],
  data() {
    return {
      localParams: {
        fov: this.cameraParams.fov,
        position: [...this.cameraParams.position],
        rotation: [...this.cameraParams.rotation]
      },
      controlMode: 'orbit',
      moveSpeed: 1.0,
      savedView: null
    }
  },
  computed: {
    distance() {
      const [x, y, z] = this.localParams.position
      return Math.sqrt(x * x + y * y + z * z)
    },
    direction() {
      const [x, y, z] = this.localParams.position
      const absX = Math.abs(x)
      const absY = Math.abs(y)
      const absZ = Math.abs(z)
      
      if (absX > absY && absX > absZ) {
        return x > 0 ? '东' : '西'
      } else if (absY > absZ) {
        return y > 0 ? '上' : '下'
      } else {
        return z > 0 ? '南' : '北'
      }
    }
  },
  watch: {
    cameraParams: {
      handler(newParams) {
        this.localParams = {
          fov: newParams.fov,
          position: [...newParams.position],
          rotation: [...newParams.rotation]
        }
      },
      deep: true
    }
  },
  methods: {
    updateCamera() {
      this.$emit('update-camera', {
        fov: this.localParams.fov,
        position: [...this.localParams.position],
        rotation: [...this.localParams.rotation]
      })
    },
    updateControlMode() {
      // 可以在这里添加控制模式切换的逻辑
      console.log('相机控制模式切换为:', this.controlMode)
    },
    updateMoveSpeed() {
      // 可以在这里添加移动速度更新的逻辑
      console.log('移动速度更新为:', this.moveSpeed)
    },
    applyPreset(preset) {
      const presets = {
        front: { position: [0, 0, 5], rotation: [0, 0, 0] },
        back: { position: [0, 0, -5], rotation: [0, 180, 0] },
        left: { position: [-5, 0, 0], rotation: [0, -90, 0] },
        right: { position: [5, 0, 0], rotation: [0, 90, 0] },
        top: { position: [0, 5, 0], rotation: [-90, 0, 0] },
        bottom: { position: [0, -5, 0], rotation: [90, 0, 0] }
      }
      
      if (presets[preset]) {
        Object.assign(this.localParams, presets[preset])
        this.updateCamera()
      }
    },
    lookAtOrigin() {
      // 计算看向原点的旋转角度
      const [x, y, z] = this.localParams.position
      const yaw = Math.atan2(x, z) * 180 / Math.PI
      const pitch = Math.atan2(-y, Math.sqrt(x * x + z * z)) * 180 / Math.PI
      
      this.localParams.rotation = [pitch, yaw, 0]
      this.updateCamera()
    },
    frameAll() {
      // 设置相机以框选所有对象
      this.localParams.position = [0, 0, 8]
      this.localParams.rotation = [0, 0, 0]
      this.localParams.fov = 60
      this.updateCamera()
    },
    saveView() {
      this.savedView = {
        fov: this.localParams.fov,
        position: [...this.localParams.position],
        rotation: [...this.localParams.rotation]
      }
      this.$message.success('视图已保存')
    },
    loadView() {
      if (this.savedView) {
        Object.assign(this.localParams, {
          fov: this.savedView.fov,
          position: [...this.savedView.position],
          rotation: [...this.savedView.rotation]
        })
        this.updateCamera()
        this.$message.success('视图已加载')
      }
    }
  }
}
</script>

<style scoped>
.camera-control-widget {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.widget-header {
  background: #f8f9fa;
  padding: 12px 16px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.widget-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.reset-btn {
  padding: 4px 8px;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: white;
  color: #6c757d;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.reset-btn:hover {
  background: #f8f9fa;
  border-color: #adb5bd;
}

.widget-content {
  padding: 16px;
}

.setting-group {
  margin-bottom: 16px;
}

.setting-group:last-child {
  margin-bottom: 0;
}

.setting-group > label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #6c757d;
  margin-bottom: 8px;
}

.vector-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.axis-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.axis-input label {
  width: 40px;
  font-size: 12px;
  color: #6c757d;
  margin: 0;
}

.preset-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.preset-btn {
  padding: 6px 12px;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: white;
  color: #495057;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.preset-btn:hover {
  background: #f8f9fa;
  border-color: #adb5bd;
}

.camera-info {
  background: #f8f9fa;
  border-radius: 4px;
  padding: 8px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item span:first-child {
  color: #6c757d;
}

.info-item span:last-child {
  color: #2c3e50;
  font-weight: 500;
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.action-btn {
  padding: 6px 8px;
  border: 1px solid #007bff;
  border-radius: 4px;
  background: white;
  color: #007bff;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn:hover:not(:disabled) {
  background: #007bff;
  color: white;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: #dee2e6;
  color: #6c757d;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
}

:deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.el-radio) {
  margin-right: 0;
}

:deep(.el-radio__label) {
  font-size: 12px;
}

:deep(.el-slider) {
  margin: 8px 0;
}
</style>
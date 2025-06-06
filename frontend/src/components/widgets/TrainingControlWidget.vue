<template>
  <div class="training-control-widget">
    <div class="widget-header">
      <h3>训练控制</h3>
      <div class="connection-status" :class="{ 'connected': isConnected }">
        <span class="status-dot"></span>
        {{ isConnected ? '已连接' : '未连接' }}
      </div>
    </div>
    
    <div class="widget-content">
      <!-- 训练状态显示 -->
      <div class="status-section">
        <div class="status-item">
          <label>当前迭代:</label>
          <span class="value">{{ currentIteration || 0 }}</span>
        </div>
        <div class="status-item">
          <label>训练状态:</label>
          <span class="value" :class="{ 'paused': trainingPaused, 'running': !trainingPaused }">
            {{ trainingPaused ? '已暂停' : '运行中' }}
          </span>
        </div>
      </div>

      <!-- 训练控制按钮 -->
      <div class="control-section">
        <button 
          @click="$emit('toggle-training')"
          :disabled="!isConnected"
          class="control-btn primary"
          :class="{ 'pause': !trainingPaused, 'resume': trainingPaused }"
        >
          {{ trainingPaused ? '恢复训练' : '暂停训练' }}
        </button>
        
        <button 
          @click="$emit('single-step')"
          :disabled="!isConnected || !trainingPaused"
          class="control-btn secondary"
        >
          单步执行
        </button>
        
        <button 
          @click="$emit('stop-training')"
          :disabled="!isConnected"
          class="control-btn danger"
        >
          停止训练
        </button>
      </div>

      <!-- 停止条件设置 -->
      <div class="settings-section">
        <div class="setting-item">
          <label for="stop-iteration">停止于迭代:</label>
          <el-input-number
            id="stop-iteration"
            v-model="stopIterationValue"
            :min="-1"
            :max="999999"
            :step="1000"
            size="small"
            @change="handleStopIterationChange"
            :disabled="!isConnected"
          />
          <small>(-1 表示不自动停止)</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TrainingControlWidget',
  props: {
    isConnected: {
      type: Boolean,
      default: false
    },
    trainingPaused: {
      type: Boolean,
      default: false
    },
    currentIteration: {
      type: Number,
      default: 0
    },
    stopAtIteration: {
      type: Number,
      default: -1
    }
  },
  emits: ['toggle-training', 'single-step', 'stop-training', 'update-stop-iteration'],
  data() {
    return {
      stopIterationValue: this.stopAtIteration
    }
  },
  watch: {
    stopAtIteration(newVal) {
      this.stopIterationValue = newVal
    }
  },
  methods: {
    handleStopIterationChange(value) {
      this.$emit('update-stop-iteration', value)
    }
  }
}
</script>

<style scoped>
.training-control-widget {
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

.connection-status {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #6c757d;
}

.connection-status.connected {
  color: #28a745;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc3545;
  margin-right: 6px;
  animation: pulse 2s infinite;
}

.connection-status.connected .status-dot {
  background: #28a745;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.widget-content {
  padding: 16px;
}

.status-section {
  margin-bottom: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
}

.status-item label {
  font-size: 12px;
  color: #6c757d;
  margin: 0;
}

.status-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.value.running {
  color: #28a745;
}

.value.paused {
  color: #ffc107;
}

.control-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.control-btn {
  padding: 10px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.control-btn.primary {
  background: #007bff;
  color: white;
}

.control-btn.primary:hover:not(:disabled) {
  background: #0056b3;
}

.control-btn.primary.pause {
  background: #ffc107;
  color: #212529;
}

.control-btn.primary.resume {
  background: #28a745;
}

.control-btn.secondary {
  background: #6c757d;
  color: white;
}

.control-btn.secondary:hover:not(:disabled) {
  background: #545b62;
}

.control-btn.danger {
  background: #dc3545;
  color: white;
}

.control-btn.danger:hover:not(:disabled) {
  background: #c82333;
}

.settings-section {
  border-top: 1px solid #e9ecef;
  padding-top: 16px;
}

.setting-item {
  margin-bottom: 12px;
}

.setting-item label {
  display: block;
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 4px;
}

.setting-item small {
  display: block;
  font-size: 11px;
  color: #6c757d;
  margin-top: 4px;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
}
</style>
<template>
  <div class="render-control-widget">
    <div class="widget-header">
      <h3>渲染控制</h3>
    </div>
    
    <div class="widget-content">
      <!-- 分辨率设置 -->
      <div class="setting-group">
        <label>分辨率</label>
        <el-select 
          v-model="localSettings.resolution" 
          @change="updateSettings"
          size="small"
          style="width: 100%"
        >
          <el-option label="512x512" :value="512" />
          <el-option label="1024x1024" :value="1024" />
          <el-option label="1536x1536" :value="1536" />
          <el-option label="2048x2048" :value="2048" />
        </el-select>
      </div>

      <!-- 渲染选项 -->
      <div class="setting-group">
        <label>渲染选项</label>
        <div class="checkbox-group">
          <el-checkbox 
            v-model="localSettings.render_alpha" 
            @change="updateSettings"
            size="small"
          >
            渲染透明度
          </el-checkbox>
          <el-checkbox 
            v-model="localSettings.render_depth" 
            @change="updateSettings"
            size="small"
          >
            渲染深度
          </el-checkbox>
          <el-checkbox 
            v-model="localSettings.render_normal" 
            @change="updateSettings"
            size="small"
          >
            渲染法线
          </el-checkbox>
        </div>
      </div>

      <!-- 背景颜色 -->
      <div class="setting-group">
        <label>背景颜色</label>
        <el-color-picker 
          v-model="localSettings.background_color" 
          @change="updateSettings"
          size="small"
          show-alpha
          color-format="hex"
        />
      </div>

      <!-- 渲染质量 -->
      <div class="setting-group">
        <label>渲染质量</label>
        <el-slider
          v-model="localSettings.quality"
          @change="updateSettings"
          :min="1"
          :max="10"
          :step="1"
          show-stops
          show-tooltip
        />
        <div class="quality-labels">
          <span>低</span>
          <span>高</span>
        </div>
      </div>

      <!-- 高级设置 -->
      <div class="setting-group">
        <el-collapse v-model="advancedOpen" size="small">
          <el-collapse-item title="高级设置" name="advanced">
            <div class="advanced-settings">
              <div class="setting-item">
                <label>SH度数:</label>
                <el-input-number
                  v-model="localSettings.sh_degree"
                  @change="updateSettings"
                  :min="0"
                  :max="3"
                  size="small"
                />
              </div>
              
              <div class="setting-item">
                <label>缩放修饰符:</label>
                <el-input-number
                  v-model="localSettings.scaling_modifier"
                  @change="updateSettings"
                  :min="0.1"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  size="small"
                />
              </div>

              <div class="setting-item">
                <el-checkbox 
                  v-model="localSettings.convert_SHs_python" 
                  @change="updateSettings"
                  size="small"
                >
                  Python SH转换
                </el-checkbox>
              </div>

              <div class="setting-item">
                <el-checkbox 
                  v-model="localSettings.compute_cov3D_python" 
                  @change="updateSettings"
                  size="small"
                >
                  Python 3D协方差
                </el-checkbox>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 快速预设 -->
      <div class="setting-group">
        <label>快速预设</label>
        <div class="preset-buttons">
          <button @click="applyPreset('fast')" class="preset-btn">快速</button>
          <button @click="applyPreset('balanced')" class="preset-btn">平衡</button>
          <button @click="applyPreset('quality')" class="preset-btn">高质量</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RenderControlWidget',
  props: {
    renderSettings: {
      type: Object,
      default: () => ({
        resolution: 1024,
        render_alpha: false,
        render_depth: false,
        render_normal: false,
        background_color: '#000000',
        quality: 5,
        sh_degree: 3,
        scaling_modifier: 1.0,
        convert_SHs_python: false,
        compute_cov3D_python: false
      })
    }
  },
  emits: ['update-settings'],
  data() {
    return {
      localSettings: { ...this.renderSettings },
      advancedOpen: []
    }
  },
  watch: {
    renderSettings: {
      handler(newSettings) {
        this.localSettings = { ...newSettings }
      },
      deep: true
    },
    'localSettings.render_alpha'(newVal) {
      if (newVal) {
        this.localSettings.render_depth = false
        this.localSettings.render_normal = false
      }
    },
    'localSettings.render_depth'(newVal) {
      if (newVal) {
        this.localSettings.render_alpha = false
        this.localSettings.render_normal = false
      }
    },
    'localSettings.render_normal'(newVal) {
      if (newVal) {
        this.localSettings.render_alpha = false
        this.localSettings.render_depth = false
      }
    }
  },
  methods: {
    updateSettings() {
      this.$emit('update-settings', { ...this.localSettings })
    },
    applyPreset(preset) {
      const presets = {
        fast: {
          resolution: 512,
          quality: 3,
          render_alpha: false,
          render_depth: false,
          render_normal: false,
          sh_degree: 1,
          scaling_modifier: 1.0
        },
        balanced: {
          resolution: 1024,
          quality: 5,
          render_alpha: false,
          render_depth: false,
          render_normal: false,
          sh_degree: 2,
          scaling_modifier: 1.0
        },
        quality: {
          resolution: 2048,
          quality: 8,
          render_alpha: false,
          render_depth: false,
          render_normal: false,
          sh_degree: 3,
          scaling_modifier: 1.0
        }
      }
      
      Object.assign(this.localSettings, presets[preset])
      this.updateSettings()
    }
  }
}
</script>

<style scoped>
.render-control-widget {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.widget-header {
  background: #f8f9fa;
  padding: 12px 16px;
  border-bottom: 1px solid #e9ecef;
}

.widget-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
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

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quality-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #6c757d;
  margin-top: 4px;
}

.advanced-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-item label {
  font-size: 12px;
  color: #6c757d;
  margin: 0;
}

.preset-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.preset-btn {
  padding: 8px 12px;
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

.preset-btn:active {
  background: #e9ecef;
}

:deep(.el-collapse-item__header) {
  font-size: 12px;
  padding: 8px 0;
}

:deep(.el-collapse-item__content) {
  padding: 8px 0;
}

:deep(.el-input-number) {
  width: 80px;
}

:deep(.el-checkbox) {
  margin-right: 0;
}

:deep(.el-checkbox__label) {
  font-size: 12px;
}

:deep(.el-slider) {
  margin: 8px 0;
}
</style>
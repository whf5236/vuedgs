<template>
  <div class="training-charts-widget">
    <div class="widget-header">
      <h3>
        <i class="fas fa-chart-line"></i>
        训练图表
      </h3>
      <div class="chart-controls">
        <button 
          class="btn btn-sm"
          :class="{ 'active': autoUpdate }"
          @click="toggleAutoUpdate"
        >
          <i class="fas fa-sync-alt"></i>
          自动更新
        </button>
        <button 
          class="btn btn-sm btn-secondary"
          @click="clearCharts"
        >
          <i class="fas fa-trash"></i>
          清空
        </button>
      </div>
    </div>
    
    <div class="widget-content">
      <div class="charts-container">
        <div 
          v-for="(plot, plotName) in trainingPlots" 
          :key="plotName" 
          class="chart-item"
        >
          <div class="chart-header">
            <h4>{{ getChartTitle(plotName) }}</h4>
            <div class="chart-info">
              <span class="current-value">
                当前值: {{ getCurrentValue(plotName) }}
              </span>
              <span class="data-points">
                数据点: {{ plot.values.length }}
              </span>
            </div>
          </div>
          <div class="chart-wrapper">
            <canvas 
              :ref="plotName + 'Chart'"
              class="training-chart"
            ></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TrainingChartsWidget',
  props: {
    trainingPlots: {
      type: Object,
      required: true
    },
    iterations: {
      type: Array,
      required: true
    },
    chartConfig: {
      type: Object,
      default: () => ({
        maxDataPoints: 500,
        updateInterval: 100,
        smoothing: true
      })
    }
  },
  
  data() {
    return {
      charts: {},
      autoUpdate: true,
      updateTimer: null,
      chartTitles: {
        num_gaussians: '高斯点数量',
        loss: '损失值',
        psnr: 'PSNR',
        learning_rate: '学习率',
        sh_degree: 'SH 度数'
      }
    }
  },
  
  mounted() {
    this.$nextTick(() => {
      this.initializeCharts()
      this.startAutoUpdate()
    })
  },
  
  beforeUnmount() {
    this.stopAutoUpdate()
    this.destroyCharts()
  },
  
  watch: {
    trainingPlots: {
      handler() {
        if (this.autoUpdate) {
          this.updateAllCharts()
        }
      },
      deep: true
    }
  },
  
  methods: {
    initializeCharts() {
      Object.keys(this.trainingPlots).forEach(plotName => {
        this.createChart(plotName)
      })
    },
    
    createChart(plotName) {
      const canvasRef = this.$refs[plotName + 'Chart']
      if (!canvasRef || !canvasRef[0]) {
        console.warn(`Canvas for ${plotName} not found`)
        return
      }
      
      const canvas = canvasRef[0]
      
      // Check if canvas has dimensions
      if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) {
        console.warn(`Canvas for ${plotName} has zero dimensions, delaying chart creation`)
        this.$nextTick(() => {
          setTimeout(() => this.createChart(plotName), 100)
        })
        return
      }
      
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        console.warn(`Failed to get 2d context for ${plotName} chart`)
        return
      }
      
      const plot = this.trainingPlots[plotName]
      
      // Store canvas context for custom drawing
      this.charts[plotName] = {
        canvas: canvas,
        ctx: ctx,
        data: plot.values,
        color: plot.color || this.getDefaultColor(plotName)
      }
      
      this.drawChart(plotName)
    },
    
    drawChart(plotName) {
      const chart = this.charts[plotName]
      if (!chart) return
      
      const { canvas, ctx, data, color } = chart
      if (!ctx || !canvas) {
        console.warn(`Canvas context is null for ${plotName} chart`)
        return
      }
      
      // Check if canvas is still valid and visible
      if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) {
        console.warn(`Canvas for ${plotName} is not visible, skipping draw`)
        return
      }
      
      try {
        const width = canvas.width = canvas.offsetWidth
        const height = canvas.height = canvas.offsetHeight
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height)
      
      if (!data || data.length === 0) return
      
      // Set up drawing parameters
      const padding = 40
      const chartWidth = width - 2 * padding
      const chartHeight = height - 2 * padding
      
      // Find min/max values
      const minValue = Math.min(...data)
      const maxValue = Math.max(...data)
      const valueRange = maxValue - minValue || 1
      
      // Draw grid
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
      ctx.lineWidth = 1
      
      // Vertical grid lines
      for (let i = 0; i <= 5; i++) {
        const x = padding + (i * chartWidth) / 5
        ctx.beginPath()
        ctx.moveTo(x, padding)
        ctx.lineTo(x, height - padding)
        ctx.stroke()
      }
      
      // Horizontal grid lines
      for (let i = 0; i <= 5; i++) {
        const y = padding + (i * chartHeight) / 5
        ctx.beginPath()
        ctx.moveTo(padding, y)
        ctx.lineTo(width - padding, y)
        ctx.stroke()
      }
      
      // Draw data line
      if (data.length > 1) {
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.beginPath()
        
        for (let i = 0; i < data.length; i++) {
          const x = padding + (i * chartWidth) / (data.length - 1)
          const y = height - padding - ((data[i] - minValue) / valueRange) * chartHeight
          
          if (i === 0) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        }
        
        ctx.stroke()
      }
      
      // Draw labels
      ctx.fillStyle = '#ffffff'
      ctx.font = '12px Arial'
      ctx.textAlign = 'center'
      
      // Y-axis labels
      for (let i = 0; i <= 5; i++) {
        const value = minValue + (i * valueRange) / 5
        const y = height - padding - (i * chartHeight) / 5
        ctx.fillText(value.toFixed(2), padding - 20, y + 4)
      }
      
      } catch (error) {
        console.error(`Error drawing chart for ${plotName}:`, error)
        // Recreate chart if drawing fails
        this.createChart(plotName)
      }
    },
    
    updateAllCharts() {
      Object.keys(this.trainingPlots).forEach(plotName => {
        this.updateChart(plotName)
      })
    },
    
    updateChart(plotName) {
      const chart = this.charts[plotName]
      const plot = this.trainingPlots[plotName]
      
      if (chart && plot) {
        chart.data = plot.values
        chart.color = plot.color || this.getDefaultColor(plotName)
        this.drawChart(plotName)
      }
    },
    
    destroyCharts() {
      // Clear canvas contexts
      Object.values(this.charts).forEach(chart => {
        if (chart && chart.ctx && chart.canvas) {
          chart.ctx.clearRect(0, 0, chart.canvas.width, chart.canvas.height)
        }
      })
      this.charts = {}
    },
    
    clearCharts() {
      if (confirm('确定要清空所有图表数据吗？')) {
        this.$emit('clear-charts')
      }
    },
    
    toggleAutoUpdate() {
      this.autoUpdate = !this.autoUpdate
      if (this.autoUpdate) {
        this.startAutoUpdate()
      } else {
        this.stopAutoUpdate()
      }
    },
    
    startAutoUpdate() {
      if (this.updateTimer) {
        clearInterval(this.updateTimer)
      }
      
      this.updateTimer = setInterval(() => {
        if (this.autoUpdate) {
          this.updateAllCharts()
        }
      }, this.chartConfig.updateInterval)
    },
    
    stopAutoUpdate() {
      if (this.updateTimer) {
        clearInterval(this.updateTimer)
        this.updateTimer = null
      }
    },
    
    getChartTitle(plotName) {
      return this.chartTitles[plotName] || plotName
    },
    
    getYAxisLabel(plotName) {
      const labels = {
        num_gaussians: '数量',
        loss: '损失值',
        psnr: 'dB',
        learning_rate: '学习率',
        sh_degree: '度数'
      }
      return labels[plotName] || '值'
    },
    
    getCurrentValue(plotName) {
      const plot = this.trainingPlots[plotName]
      if (plot && plot.values.length > 0) {
        const value = plot.values[plot.values.length - 1]
        return this.formatValue(value, plot.dtype)
      }
      return 'N/A'
    },
    
    formatValue(value, dtype) {
      if (value === null || value === undefined) return 'N/A'
      
      if (dtype === 'int') {
        return Math.round(value).toLocaleString()
      } else if (dtype === 'float') {
        if (Math.abs(value) < 0.001) {
          return value.toExponential(3)
        } else {
          return value.toFixed(4)
        }
      }
      return value.toString()
    },
    
    getDefaultColor(plotName) {
      const colors = {
        num_gaussians: '#3498db',
        loss: '#e74c3c',
        psnr: '#2ecc71',
        learning_rate: '#f39c12',
        sh_degree: '#9b59b6'
      }
      return colors[plotName] || '#34495e'
    },
    
    getBackgroundColor(borderColor) {
      // 将边框颜色转换为半透明背景色
      const hex = borderColor.replace('#', '')
      const r = parseInt(hex.substr(0, 2), 16)
      const g = parseInt(hex.substr(2, 2), 16)
      const b = parseInt(hex.substr(4, 2), 16)
      return `rgba(${r}, ${g}, ${b}, 0.1)`
    }
  }
}
</script>

<style scoped>
.training-charts-widget {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.widget-header {
  background: #2ecc71;
  color: white;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 8px 8px 0 0;
}

.widget-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.widget-header i {
  margin-right: 8px;
}

.chart-controls {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-sm {
  background: rgba(255,255,255,0.2);
  color: white;
}

.btn-sm:hover {
  background: rgba(255,255,255,0.3);
}

.btn-sm.active {
  background: rgba(255,255,255,0.9);
  color: #2ecc71;
}

.btn-secondary {
  background: rgba(255,255,255,0.2);
  color: white;
}

.btn-secondary:hover {
  background: rgba(255,255,255,0.3);
}

.widget-content {
  flex: 1;
  padding: 16px;
  overflow: hidden;
}

.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  height: 100%;
}

.chart-item {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #dee2e6;
}

.chart-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.chart-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.current-value {
  font-size: 12px;
  font-weight: 600;
  color: #27ae60;
}

.data-points {
  font-size: 11px;
  color: #6c757d;
}

.chart-wrapper {
  flex: 1;
  position: relative;
  min-height: 200px;
}

.training-chart {
  width: 100% !important;
  height: 100% !important;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .charts-container {
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  }
}

@media (max-width: 768px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
  
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .chart-info {
    align-items: flex-start;
  }
}
</style>
<template>
  <div class="training-stats-widget">
    <div class="widget-header">
      <h3>训练统计</h3>
      <div class="header-actions">
        <button @click="clearStats" class="clear-btn">
          清除
        </button>
        <button @click="exportStats" class="export-btn">
          导出
        </button>
      </div>
    </div>
    
    <div class="widget-content">
      <!-- 当前统计信息 -->
      <div class="stats-overview">
        <div class="stat-item">
          <div class="stat-label">当前迭代</div>
          <div class="stat-value">{{ currentStats.iteration || 0 }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">高斯数量</div>
          <div class="stat-value">{{ formatNumber(currentStats.num_gaussians) }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">当前损失</div>
          <div class="stat-value">{{ formatLoss(currentStats.loss) }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">SH 阶数</div>
          <div class="stat-value">{{ currentStats.sh_degree || 0 }}</div>
        </div>
      </div>

      <!-- 训练进度 -->
      <div class="progress-section">
        <div class="progress-header">
          <span>训练进度</span>
          <span>{{ progressPercentage }}%</span>
        </div>
        <el-progress 
          :percentage="progressPercentage" 
          :stroke-width="8"
          :show-text="false"
        />
        <div class="progress-info">
          <span>{{ currentStats.iteration || 0 }} / {{ maxIterations }}</span>
          <span>预计剩余: {{ estimatedTimeRemaining }}</span>
        </div>
      </div>

      <!-- 损失曲线图 -->
      <div class="chart-section">
        <div class="chart-header">
          <span>损失曲线</span>
          <div class="chart-controls">
            <el-checkbox v-model="showMovingAverage" size="small">
              移动平均
            </el-checkbox>
            <el-select v-model="chartTimeRange" size="small" style="width: 100px">
              <el-option label="全部" value="all" />
              <el-option label="最近100" value="100" />
              <el-option label="最近500" value="500" />
              <el-option label="最近1000" value="1000" />
            </el-select>
          </div>
        </div>
        <div class="chart-container" ref="lossChart">
          <!-- 这里将使用 Chart.js 或其他图表库 -->
          <canvas ref="lossCanvas" width="400" height="200"></canvas>
        </div>
      </div>

      <!-- 高斯数量曲线图 -->
      <div class="chart-section">
        <div class="chart-header">
          <span>高斯数量变化</span>
        </div>
        <div class="chart-container" ref="gaussianChart">
          <canvas ref="gaussianCanvas" width="400" height="150"></canvas>
        </div>
      </div>

      <!-- 详细统计信息 -->
      <div class="detailed-stats">
        <div class="stats-header">
          <span>详细统计</span>
          <button @click="toggleDetailedStats" class="toggle-btn">
            {{ showDetailedStats ? '收起' : '展开' }}
          </button>
        </div>
        <div v-show="showDetailedStats" class="stats-details">
          <div class="detail-row">
            <span>平均损失:</span>
            <span>{{ formatLoss(averageLoss) }}</span>
          </div>
          <div class="detail-row">
            <span>最小损失:</span>
            <span>{{ formatLoss(minLoss) }}</span>
          </div>
          <div class="detail-row">
            <span>最大损失:</span>
            <span>{{ formatLoss(maxLoss) }}</span>
          </div>
          <div class="detail-row">
            <span>训练时间:</span>
            <span>{{ formatDuration(trainingDuration) }}</span>
          </div>
          <div class="detail-row">
            <span>平均迭代时间:</span>
            <span>{{ formatDuration(averageIterationTime) }}</span>
          </div>
          <div class="detail-row">
            <span>最大高斯数:</span>
            <span>{{ formatNumber(maxGaussians) }}</span>
          </div>
        </div>
      </div>

      <!-- 训练参数显示 -->
      <div class="params-section" v-if="currentStats.train_params">
        <div class="params-header">
          <span>训练参数</span>
        </div>
        <div class="params-grid">
          <div v-for="(value, key) in currentStats.train_params" :key="key" class="param-item">
            <span class="param-key">{{ formatParamKey(key) }}:</span>
            <span class="param-value">{{ formatParamValue(value) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Chart from 'chart.js/auto'

export default {
  name: 'TrainingStatsWidget',
  props: {
    trainingData: {
      type: Object,
      default: () => ({})
    },
    maxIterations: {
      type: Number,
      default: 30000
    }
  },
  data() {
    return {
      currentStats: {},
      lossHistory: [],
      gaussianHistory: [],
      showMovingAverage: true,
      chartTimeRange: 'all',
      showDetailedStats: false,
      lossChart: null,
      gaussianChart: null,
      trainingStartTime: null,
      lossChartObserver: null,
      gaussianChartObserver: null,
      chartsInitialized: false,
      chartInitAttempts: 0,
      maxChartInitAttempts: 5
    }
  },
  computed: {
    progressPercentage() {
      if (!this.currentStats.iteration || !this.maxIterations) return 0
      return Math.min(100, (this.currentStats.iteration / this.maxIterations) * 100)
    },
    averageLoss() {
      if (this.lossHistory.length === 0) return 0
      const sum = this.lossHistory.reduce((acc, item) => acc + item.loss, 0)
      return sum / this.lossHistory.length
    },
    minLoss() {
      if (this.lossHistory.length === 0) return 0
      return Math.min(...this.lossHistory.map(item => item.loss))
    },
    maxLoss() {
      if (this.lossHistory.length === 0) return 0
      return Math.max(...this.lossHistory.map(item => item.loss))
    },
    maxGaussians() {
      if (this.gaussianHistory.length === 0) return 0
      return Math.max(...this.gaussianHistory.map(item => item.count))
    },
    trainingDuration() {
      if (!this.trainingStartTime) return 0
      return Date.now() - this.trainingStartTime
    },
    averageIterationTime() {
      if (this.lossHistory.length < 2) return 0
      const totalTime = this.trainingDuration
      return totalTime / this.lossHistory.length
    },
    estimatedTimeRemaining() {
      if (!this.currentStats.iteration || !this.averageIterationTime) return '未知'
      const remainingIterations = this.maxIterations - this.currentStats.iteration
      const remainingTime = remainingIterations * this.averageIterationTime
      return this.formatDuration(remainingTime)
    },
    filteredLossData() {
      if (this.chartTimeRange === 'all') return this.lossHistory
      const limit = parseInt(this.chartTimeRange)
      return this.lossHistory.slice(-limit)
    }
  },
  watch: {
    trainingData: {
      handler(newData) {
        this.updateStats(newData)
      },
      deep: true
    },
    filteredLossData() {
      this.updateLossChart()
    },
    gaussianHistory() {
      this.updateGaussianChart()
    }
  },
  mounted() {
    // 延迟初始化，确保DOM已完全渲染
    this.trainingStartTime = Date.now()
    
    // 等待组件完全挂载并可见
    setTimeout(() => {
      this.initChartsIfVisible()
    }, 1000)
  },
  beforeUnmount() {
    // 清理 ResizeObserver
    this.cleanupObservers()
    
    // 销毁图表
    this.destroyCharts()
  },
  methods: {
    cleanupObservers() {
      if (this.lossChartObserver) {
        this.lossChartObserver.disconnect()
        this.lossChartObserver = null
      }
      if (this.gaussianChartObserver) {
        this.gaussianChartObserver.disconnect()
        this.gaussianChartObserver = null
      }
    },
    
    destroyCharts() {
      if (this.lossChart) {
        this.lossChart.destroy()
        this.lossChart = null
      }
      if (this.gaussianChart) {
        this.gaussianChart.destroy()
        this.gaussianChart = null
      }
    },
    
    initChartsIfVisible() {
      // 检查组件是否可见
      if (!this.$el || !this.$el.offsetParent) {
        console.log('TrainingStatsWidget 不可见，延迟初始化图表')
        if (this.chartInitAttempts < this.maxChartInitAttempts) {
          this.chartInitAttempts++
          setTimeout(() => this.initChartsIfVisible(), 1000)
        }
        return
      }
      
      // 组件可见，初始化图表
      console.log('TrainingStatsWidget 可见，开始初始化图表')
      this.setupResizeObservers()
      this.initCharts()
    },
    
    setupResizeObservers() {
      this.cleanupObservers()
      
      // 为损失图表容器创建 ResizeObserver
      if (this.$refs.lossChart) {
        this.lossChartObserver = new ResizeObserver((entries) => {
          // 使用 requestAnimationFrame 避免 ResizeObserver 循环
          window.requestAnimationFrame(() => {
            if (!entries.length) return
            
            const entry = entries[0]
            if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
              if (!this.lossChart) {
                this.initLossChart()
              }
            }
          })
        })
        this.lossChartObserver.observe(this.$refs.lossChart)
      }
      
      // 为高斯图表容器创建 ResizeObserver
      if (this.$refs.gaussianChart) {
        this.gaussianChartObserver = new ResizeObserver((entries) => {
          // 使用 requestAnimationFrame 避免 ResizeObserver 循环
          window.requestAnimationFrame(() => {
            if (!entries.length) return
            
            const entry = entries[0]
            if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
              if (!this.gaussianChart) {
                this.initGaussianChart()
              }
            }
          })
        })
        this.gaussianChartObserver.observe(this.$refs.gaussianChart)
      }
    },
    updateStats(data) {
      this.currentStats = { ...data }
      
      // 更新损失历史
      if (data.loss !== undefined && data.iteration !== undefined) {
        this.lossHistory.push({
          iteration: data.iteration,
          loss: data.loss,
          timestamp: Date.now()
        })
        
        // 限制历史数据长度
        if (this.lossHistory.length > 10000) {
          this.lossHistory = this.lossHistory.slice(-5000)
        }
      }
      
      // 更新高斯数量历史
      if (data.num_gaussians !== undefined && data.iteration !== undefined) {
        this.gaussianHistory.push({
          iteration: data.iteration,
          count: data.num_gaussians,
          timestamp: Date.now()
        })
        
        // 限制历史数据长度
        if (this.gaussianHistory.length > 10000) {
          this.gaussianHistory = this.gaussianHistory.slice(-5000)
        }
      }
    },
    initCharts() {
      this.initLossChart()
      this.initGaussianChart()
    },
    initLossChart() {
      if (!this.$refs.lossCanvas) {
        console.warn('lossCanvas ref not found')
        return
      }
      
      // Destroy existing chart if it exists
      if (this.lossChart) {
        this.lossChart.destroy()
        this.lossChart = null
      }
      
      const ctx = this.$refs.lossCanvas.getContext('2d')
      if (!ctx) {
        console.warn('Failed to get 2d context from lossCanvas')
        return
      }
      
      this.lossChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: '损失',
            data: [],
            borderColor: '#007bff',
            backgroundColor: 'rgba(0, 123, 255, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              title: {
                display: true,
                text: '迭代次数'
              }
            },
            y: {
              title: {
                display: true,
                text: '损失值'
              },
              type: 'logarithmic'
            }
          },
          plugins: {
            legend: {
              display: false
            }
          }
        }
      })
    },
    initGaussianChart() {
      if (!this.$refs.gaussianCanvas) {
        console.warn('gaussianCanvas ref not found')
        return
      }
      
      // Destroy existing chart if it exists
      if (this.gaussianChart) {
        this.gaussianChart.destroy()
        this.gaussianChart = null
      }
      
      const ctx = this.$refs.gaussianCanvas.getContext('2d')
      if (!ctx) {
        console.warn('Failed to get 2d context from gaussianCanvas')
        return
      }
      
      this.gaussianChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: '高斯数量',
            data: [],
            borderColor: '#28a745',
            backgroundColor: 'rgba(40, 167, 69, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              title: {
                display: true,
                text: '迭代次数'
              }
            },
            y: {
              title: {
                display: true,
                text: '高斯数量'
              }
            }
          },
          plugins: {
            legend: {
              display: false
            }
          }
        }
      })
    },
    updateLossChart() {
      if (!this.lossChart || !this.lossChart.ctx || !this.lossChart.canvas) {
        console.warn('Loss chart not available for update')
        return
      }
      
      // Check if canvas is still valid
      if (!this.$refs.lossCanvas || this.$refs.lossCanvas.offsetWidth === 0) {
        console.warn('Loss canvas is not visible, skipping update')
        return
      }
      
      try {
        const data = this.filteredLossData
        this.lossChart.data.labels = data.map(item => item.iteration)
        this.lossChart.data.datasets[0].data = data.map(item => item.loss)
        
        if (this.showMovingAverage && data.length > 10) {
          const movingAvg = this.calculateMovingAverage(data.map(item => item.loss), 10)
          if (this.lossChart.data.datasets.length === 1) {
            this.lossChart.data.datasets.push({
              label: '移动平均',
              data: movingAvg,
              borderColor: '#ffc107',
              backgroundColor: 'transparent',
              borderWidth: 2,
              fill: false,
              tension: 0.1
            })
          } else {
            this.lossChart.data.datasets[1].data = movingAvg
          }
        } else if (this.lossChart.data.datasets.length > 1) {
          this.lossChart.data.datasets.splice(1, 1)
        }
        
        this.lossChart.update('none')
      } catch (error) {
        console.error('Error updating loss chart:', error)
        // Reinitialize chart if update fails
        this.initLossChart()
      }
    },
    updateGaussianChart() {
      if (!this.gaussianChart || !this.gaussianChart.ctx || !this.gaussianChart.canvas) {
        console.warn('Gaussian chart not available for update')
        return
      }
      
      // Check if canvas is still valid
      if (!this.$refs.gaussianCanvas || this.$refs.gaussianCanvas.offsetWidth === 0) {
        console.warn('Gaussian canvas is not visible, skipping update')
        return
      }
      
      try {
        this.gaussianChart.data.labels = this.gaussianHistory.map(item => item.iteration)
        this.gaussianChart.data.datasets[0].data = this.gaussianHistory.map(item => item.count)
        this.gaussianChart.update('none')
      } catch (error) {
        console.error('Error updating gaussian chart:', error)
        // Reinitialize chart if update fails
        this.initGaussianChart()
      }
    },
    calculateMovingAverage(data, windowSize) {
      const result = []
      for (let i = 0; i < data.length; i++) {
        const start = Math.max(0, i - windowSize + 1)
        const window = data.slice(start, i + 1)
        const avg = window.reduce((sum, val) => sum + val, 0) / window.length
        result.push(avg)
      }
      return result
    },
    formatNumber(num) {
      if (num === undefined || num === null) return '0'
      if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M'
      } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K'
      }
      return num.toString()
    },
    formatLoss(loss) {
      if (loss === undefined || loss === null) return '0.000'
      return parseFloat(loss).toExponential(3)
    },
    formatDuration(ms) {
      if (!ms) return '0s'
      const seconds = Math.floor(ms / 1000)
      const minutes = Math.floor(seconds / 60)
      const hours = Math.floor(minutes / 60)
      
      if (hours > 0) {
        return `${hours}h ${minutes % 60}m`
      } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`
      } else {
        return `${seconds}s`
      }
    },
    formatParamKey(key) {
      return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    },
    formatParamValue(value) {
      if (typeof value === 'number') {
        return value.toFixed(6)
      }
      return value.toString()
    },
    clearStats() {
      this.$confirm('确定要清除所有统计数据吗？', '确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.lossHistory = []
        this.gaussianHistory = []
        this.currentStats = {}
        this.trainingStartTime = Date.now()
        this.updateLossChart()
        this.updateGaussianChart()
        this.$message.success('统计数据已清除')
      })
    },
    exportStats() {
      const data = {
        lossHistory: this.lossHistory,
        gaussianHistory: this.gaussianHistory,
        currentStats: this.currentStats,
        trainingDuration: this.trainingDuration
      }
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `training_stats_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      this.$message.success('统计数据已导出')
    },
    toggleDetailedStats() {
      this.showDetailedStats = !this.showDetailedStats
    }
  }
}
</script>

<style scoped>
.training-stats-widget {
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

.header-actions {
  display: flex;
  gap: 8px;
}

.clear-btn, .export-btn {
  padding: 4px 8px;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: white;
  color: #6c757d;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.clear-btn:hover {
  background: #f8f9fa;
  border-color: #dc3545;
  color: #dc3545;
}

.export-btn:hover {
  background: #f8f9fa;
  border-color: #28a745;
  color: #28a745;
}

.widget-content {
  padding: 16px;
}

.stats-overview {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.stat-label {
  font-size: 11px;
  color: #6c757d;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: #6c757d;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 11px;
  color: #6c757d;
}

.chart-section {
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 12px;
  color: #6c757d;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-container {
  position: relative;
  height: 200px;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 8px;
}
/*
.chart-container canvas {
  width: 100% !important;
  height: 100% !important;
}
*/
.detailed-stats {
  margin-bottom: 16px;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: #6c757d;
}

.toggle-btn {
  padding: 2px 6px;
  border: 1px solid #dee2e6;
  border-radius: 3px;
  background: white;
  color: #6c757d;
  font-size: 11px;
  cursor: pointer;
}

.stats-details {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 11px;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-row span:first-child {
  color: #6c757d;
}

.detail-row span:last-child {
  color: #2c3e50;
  font-weight: 500;
}

.params-section {
  margin-bottom: 16px;
}

.params-header {
  margin-bottom: 8px;
  font-size: 12px;
  color: #6c757d;
}

.params-grid {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.param-key {
  color: #6c757d;
}

.param-value {
  color: #2c3e50;
  font-weight: 500;
  font-family: monospace;
}

:deep(.el-progress-bar__outer) {
  background-color: #e9ecef;
}

:deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #007bff, #28a745);
}

:deep(.el-checkbox) {
  margin-right: 0;
}

:deep(.el-checkbox__label) {
  font-size: 11px;
}
</style>
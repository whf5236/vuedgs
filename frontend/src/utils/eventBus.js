import { reactive } from 'vue'

// 创建一个简单的事件总线
export const eventBus = {
  state: reactive({
    events: {}
  }),
  
  // 注册事件监听器
  on(event, callback) {
    if (!this.state.events[event]) {
      this.state.events[event] = []
    }
    this.state.events[event].push(callback)
  },
  
  // 移除事件监听器
  off(event, callback) {
    if (!this.state.events[event]) return
    
    if (!callback) {
      // 如果没有提供回调函数，移除所有该事件的监听器
      this.state.events[event] = []
      return
    }
    
    this.state.events[event] = this.state.events[event].filter(
      cb => cb !== callback
    )
  },
  
  // 触发事件
  emit(event, ...args) {
    if (!this.state.events[event]) return
    
    this.state.events[event].forEach(callback => {
      callback(...args)
    })
  }
}

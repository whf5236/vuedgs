import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import axios from 'axios'
import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import Particles from 'vue3-particles'

// 导入公共样式
import './assets/styles/common.css'
// 导入 Element Plus 样式修复
import './assets/styles/element-plus-fixes.css'

// 全局错误处理器，用于捕获并忽略 ResizeObserver 循环错误
const originalConsoleError = window.console.error;
window.console.error = (...args) => {
  // 检查错误消息是否包含 ResizeObserver 循环错误
  if (args.length > 0 && typeof args[0] === 'string' && 
      (args[0].includes('ResizeObserver loop') || 
       args[0].includes('ResizeObserver loop completed with undelivered notifications'))) {
    // 忽略 ResizeObserver 循环错误
    return;
  }
  // 对于其他错误，使用原始的 console.error
  originalConsoleError.apply(console, args);
};

// 设置全局 axios 默认值
const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

// 添加请求拦截器，确保每个请求都带有最新的 token
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 添加响应拦截器，处理401错误
axios.interceptors.response.use(
  response => {
    return response
  },
  error => {
    // 检查是否是网络错误（例如，服务器关闭）或401错误
    const isNetworkError = error.code === 'ERR_NETWORK';
    const is401Error = error.response && error.response.status === 401;

    if (isNetworkError || is401Error) {
      // 只有在当前不在登录页时才执行登出和跳转
      if (router.currentRoute.value.path !== '/login') {
        store.dispatch('logout').then(() => {
          if (isNetworkError) {
            // 使用 ElMessage 显示网络错误提示
            ElMessage({
              message: '网络错误，后端服务可能已关闭。已自动登出。',
              type: 'error',
              duration: 5000,
              showClose: true
            });
          } else {
            // 使用 ElMessage 显示认证错误提示
            ElMessage({
              message: '认证失败，Token可能已过期或无效。已自动登出。',
              type: 'warning',
              duration: 5000,
              showClose: true
            });
          }
          router.push('/login');
        });
      }
    }
    return Promise.reject(error);
  }
)

const app = createApp(App)

// 注册所有Element Plus图标组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 使用插件
app.use(store)
app.use(router)
app.use(ElementPlus, { size: 'default' })
app.use(Particles) // <--- 关键的新增行

// 挂载应用
app.mount('#app')
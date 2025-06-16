import { createStore } from 'vuex'
import axios from 'axios'

// API base URL
const API_URL = 'http://localhost:5000/api'

// 从localStorage加载训练状态
function loadTrainingState() {
  try {
    const saved = localStorage.getItem('trainingState')
    if (saved) {
      const parsed = JSON.parse(saved)
      // 不恢复client对象，因为它不能序列化
      return {
        ...parsed,
        client: null
      }
    }
  } catch (e) {
    console.warn('Failed to load training state from localStorage:', e)
  }
  return {
    connected: false,

    stats: {
      iteration: 0,
      num_gaussians: 0,
      loss: 0,
      psnr: 0,
      sh_degree: 0,
      paused: false,
      training_params: {}
    },
    currentImage: null,
    paused: false,
    client: null,
    currentTask: null,
    outputLogs: []
  }
}

// 保存训练状态到localStorage
function saveTrainingState(state) {
  try {
    // 不保存client对象，因为它不能序列化
    const toSave = {
      ...state,
      client: null
    }
    localStorage.setItem('trainingState', JSON.stringify(toSave))
  } catch (e) {
    console.warn('Failed to save training state to localStorage:', e)
  }
}

// 初始状态
const initialState = {
  token: localStorage.getItem('token') || null,
  username: localStorage.getItem('username') || null,
  user: localStorage.getItem('username') ? { username: localStorage.getItem('username') } : null, // 从localStorage恢复user对象
  status: '',
  // 训练状态管理
  training: loadTrainingState(),
  // WebSocket client removed
}

export default createStore({
  state: initialState,
  getters: {
    isAuthenticated: state => !!state.token,
    authStatus: state => state.status,
    user: state => state.user,
    // 训练相关 getters
    trainingConnected: state => state.training.connected,
    trainingStats: state => state.training.stats,
    trainingImage: state => state.training.currentImage,
    trainingPaused: state => state.training.paused,
    trainingClient: state => state.training.client,
    trainingCurrentTask: state => state.training.currentTask,
    trainingOutputLogs: state => state.training.outputLogs
  },
  mutations: {
    AUTH_REQUEST(state) {
      state.status = 'loading'
    },
    AUTH_SUCCESS(state, { token, user }) {
      state.status = 'success'
      state.token = token
      state.user = user
      state.username = user.username
    },
    AUTH_ERROR(state) {
      state.status = 'error'
    },
    LOGOUT(state) {
      state.status = ''
      state.token = null
      state.username = null
      state.user = null
    },
    // 训练相关mutations
    SET_TRAINING_CONNECTION(state, isConnected) {
      state.training.connected = isConnected
      saveTrainingState(state.training)
    },
    UPDATE_TRAINING_STATS(state, stats) {
      state.training.stats = { ...state.training.stats, ...stats }
      state.training.paused = stats.paused || false
      saveTrainingState(state.training)
    },
    SET_TRAINING_IMAGE(state, image) {
      state.training.currentImage = image
      // 不保存图像到localStorage，因为太大
    },
    SET_TRAINING_CLIENT(state, client) {
      state.training.client = client
      // 不保存client到localStorage，因为不能序列化
    },
    SET_TRAINING_TASK(state, task) {
      state.training.currentTask = task
      saveTrainingState(state.training)
    },
    UPDATE_TRAINING_LOGS(state, logs) {
      state.training.outputLogs = logs
      saveTrainingState(state.training)
    },
    APPEND_TRAINING_LOG(state, log) {
      state.training.outputLogs.push(log)
      saveTrainingState(state.training)
    },
    RESET_TRAINING_STATE(state) {
      state.training.connected = false
      state.training.stats = {
        iteration: 0,
        num_gaussians: 0,
        loss: 0,
        psnr: 0,
        sh_degree: 0,
        paused: false,
        training_params: {}
      }
      state.training.currentImage = null
      state.training.paused = false
      state.training.client = null
      state.training.currentTask = null
      state.training.outputLogs = []
      saveTrainingState(state.training)
    },
    // 添加缺失的 mutation
    setToken(state, token) {
      state.token = token
      localStorage.setItem('token', token)
    },
    setUsername(state, username) {
      state.username = username
      state.user = { username: username }
      localStorage.setItem('username', username)
    },
    // WebSocket initialization removed
  },
  actions: {
    async login({ commit }, credentials) {
      try {
        // 首先进行 HTTP 登录
        const response = await axios.post(`${API_URL}/login`, credentials);
        const { access_token, username } = response.data;
        
        // 保存认证信息
        commit('setToken', access_token);
        commit('setUsername', username);
        // WebSocket initialization removed
        
        // 清除路由守卫中的token验证缓存
        if (window.tokenValidationCache) {
          window.tokenValidationCache = {
            token: null,
            isValid: false,
            lastCheck: 0,
            cacheTimeout: 5 * 60 * 1000
          }
        }
        
        // Socket.IO connection removed
        
        return Promise.resolve(true);
      } catch (error) {
        console.error('登录失败:', error);
        return Promise.reject(error);
      }
    },
    async register({ commit }, user) {
      commit('AUTH_REQUEST')
      
      try {
        let response;
        
        // 使用HTTP API进行注册
        response = await axios.post(`${API_URL}/register`, user)
        
        commit('AUTH_SUCCESS', { token: null, user: null });
        return response
      } catch (err) {
        commit('AUTH_ERROR')
        throw err
      }
    },
    logout({ commit, state }) {
      return new Promise(resolve => {
        // 清理store状态
        commit('LOGOUT')
        commit('RESET_TRAINING_STATE')
        
        // 清理localStorage
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.removeItem('trainingState')
        
        // 清理axios默认headers
        delete axios.defaults.headers.common['Authorization']
        
        // 断开WebSocket连接
        if (state.ws) {
          state.ws.disconnect()
        }
        
        resolve()
      })
    },
    // 训练相关actions
    initTrainingClient({ commit, state }) {
      if (state.training.client) {
        return state.training.client
      }
      
      // 这里需要导入TrainingVisualizationClient类
      // 由于循环依赖问题，我们在组件中创建client并传递给store
      return null
    },
    setTrainingClient({ commit }, client) {
      commit('SET_TRAINING_CLIENT', client)
    },
    updateTrainingConnection({ commit }, isConnected) {
      commit('SET_TRAINING_CONNECTION', isConnected)
    },
    updateTrainingStats({ commit }, stats) {
      commit('UPDATE_TRAINING_STATS', stats)
    },
    updateTrainingImage({ commit }, image) {
      commit('SET_TRAINING_IMAGE', image)
    },
    setTrainingTask({ commit }, task) {
      commit('SET_TRAINING_TASK', task)
    },
    updateTrainingLogs({ commit }, logs) {
      commit('UPDATE_TRAINING_LOGS', logs)
    },
    appendTrainingLog({ commit }, log) {
      commit('APPEND_TRAINING_LOG', log)
    },
    resetTrainingState({ commit }) {
      commit('RESET_TRAINING_STATE')
    },
    clearTrainingTask({ commit }) {
      commit('SET_TRAINING_TASK', null)
    }
  }
})

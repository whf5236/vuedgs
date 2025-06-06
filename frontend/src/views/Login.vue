<template>
  <div class="login">
    <div class="row justify-content-center">
      <div class="col-md-6">
        <div class="card shadow">
          <div class="card-body p-5">
            <h2 class="text-center mb-4 text-primary">登录</h2>
            
            <div v-if="error" class="alert alert-danger">
              {{ error }}
            </div>
            
            <form @submit.prevent="handleLogin({ username, password })">
              <div class="mb-3">
                <label for="username" class="form-label">用户名</label>
                <div class="input-group">
                  <span class="input-group-text"><i class="fas fa-user"></i></span>
                  <input 
                    type="text" 
                    class="form-control" 
                    id="username" 
                    v-model="username" 
                    required
                    placeholder="请输入您的用户名"
                  >
                </div>
              </div>
              
              <div class="mb-4">
                <label for="password" class="form-label">密码</label>
                <div class="input-group">
                  <span class="input-group-text"><i class="fas fa-lock"></i></span>
                  <input 
                    type="password" 
                    class="form-control" 
                    id="password" 
                    v-model="password" 
                    required
                    placeholder="请输入您的密码"
                  >
                </div>
              </div>
              
              <div class="d-grid">
                <button type="submit" class="btn btn-primary btn-lg" :disabled="loading">
                  <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                  {{ loading ? 'Logging in...' : 'Login' }}
                </button>
              </div>
            </form>
            
            <div class="text-center mt-4">
              <p>没有账号? <router-link to="/register">注册</router-link></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'

export default {
  setup() {
    const router = useRouter()
    const store = useStore()
    
    // 定义响应式变量
    const username = ref('')
    const password = ref('')
    const loading = ref(false)
    const error = ref('')

    const handleLogin = async (formData) => {
      try {
        loading.value = true
        error.value = ''
        console.log('发送登录请求:', formData)
        
        // 调用登录 action 并等待结果
        await store.dispatch('login', formData)
        console.log('登录成功，准备跳转到仪表盘')
        
        // 在跳转前添加短暂延迟，确保认证状态已更新
        setTimeout(() => {
          // 检查是否仍在登录页面，避免在路由守卫已经处理的情况下重复跳转
          if (router.currentRoute.value.path === '/login') {
            console.log('从登录页面跳转到仪表盘')
            router.push({ name: 'Dashboard' }).catch(err => {
              if (err.name !== 'NavigationDuplicated') {
                console.error('导航错误:', err)
              }
            })
          } else {
            console.log('路由守卫已处理跳转，当前路由:', router.currentRoute.value.path)
          }
        }, 100)
      } catch (err) {
        console.error('登录失败:', err)
        error.value = err.response?.data?.message || '登录失败，请重试'
      } finally {
        loading.value = false
      }
    }

    return {
      username,
      password,
      loading,
      error,
      handleLogin
    }
  }
}
</script>

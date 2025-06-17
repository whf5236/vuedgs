<template>
  <div class="login">
    <div class="card shadow">
      <div class="card-body p-5">
        <h2 class="text-center mb-4">登录</h2>
        
        <div v-if="error" class="alert alert-danger">
          {{ error }}
        </div>
        
        <form @submit.prevent="handleLogin({ username, password })">
          <div class="mb-3">
            <label for="username" class="form-label">用户名</label>
            <div class="custom-input-group">
              <i class="fas fa-user input-icon"></i>
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
            <div class="custom-input-group">
              <i class="fas fa-lock input-icon"></i>
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
              {{ loading ? 'Logging in...' : '登录' }}
            </button>
          </div>
        </form>
        
        <div class="text-center mt-4">
          <p>没有账号? <router-link to="/register">注册</router-link></p>
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
  name: 'LoginPage',
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
        
        // 调用登录 action 并等待结果
        await store.dispatch('login', formData)
        
        // 在跳转前添加短暂延迟，确保认证状态已更新
        setTimeout(() => {
          // 检查是否仍在登录页面，避免在路由守卫已经处理的情况下重复跳转
          if (router.currentRoute.value.path === '/login') {
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

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  width: 100%;
}

.card {
  width: 100%;
  max-width: 420px; /* Control form width */
  background-color: rgba(255, 255, 255, 0.15); /* Semi-transparent background */
  backdrop-filter: blur(10px); /* Frosted glass effect */
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 15px; /* Softer corners */
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.card-body {
  padding: 3rem !important;
}

/* New styles for custom input group */
.custom-input-group {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 15px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 255, 255, 0.7);
  z-index: 10;
}

.form-control {
  background-color: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 8px; /* Add some radius */
  color: white;
  padding-left: 45px; /* Make space for the icon */
  height: 48px; /* Taller inputs */
}

.form-control:focus {
  background-color: rgba(255, 255, 255, 0.3);
  box-shadow: none;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.form-control::placeholder {
  color: rgba(255, 255, 255, 0.7);
}

h2 {
  color: #fff !important;
  font-weight: 600;
}

.form-label, p, a {
  color: #fff !important;
}

.btn-primary {
  border-radius: 8px;
  height: 48px;
}

a:hover {
  text-decoration: underline;
}
</style>

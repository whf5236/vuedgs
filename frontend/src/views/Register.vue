<template>
  <div class="register">
    <div class="card shadow">
      <div class="card-body p-5">
        <h2 class="text-center mb-4">注册</h2>
        
        <div v-if="error" class="alert alert-danger">
          {{ error }}
        </div>
        
        <div v-if="success" class="alert alert-success">
          {{ success }}
        </div>
        
        <form @submit.prevent="register">
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
          
          <div class="mb-3">
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
          
          <div class="mb-4">
            <label for="confirmPassword" class="form-label">确认密码</label>
            <div class="custom-input-group">
              <i class="fas fa-lock input-icon"></i>
              <input 
                type="password" 
                class="form-control" 
                id="confirmPassword" 
                v-model="confirmPassword" 
                required
                placeholder="请再次输入您的密码"
              >
            </div>
            <div v-if="passwordMismatch" class="text-danger mt-1">
              密码不匹配
            </div>
          </div>
          
          <div class="d-grid">
            <button type="submit" class="btn btn-primary btn-lg" :disabled="loading || passwordMismatch">
              <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
              {{ loading ? 'Registering...' : 'Register' }}
            </button>
          </div>
        </form>
        
        <div class="text-center mt-4">
          <p>已有帐户? <router-link to="/login">登录</router-link></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Register',
  data() {
    return {
      username: '',
      password: '',
      confirmPassword: '',
      error: null,
      success: null,
      loading: false
    }
  },
  computed: {
    passwordMismatch() {
      return this.password && this.confirmPassword && this.password !== this.confirmPassword
    }
  },
  methods: {
    register() {
      if (this.passwordMismatch) {
        return
      }
      
      this.loading = true
      this.error = null
      this.success = null
      
      const userData = {
        username: this.username,
        password: this.password
      }
      
      this.$store.dispatch('register', userData)
        .then(response => {
          this.success = 'Registration successful! You can now login.'
          this.username = ''
          this.password = ''
          this.confirmPassword = ''
          
          // Redirect to login after 2 seconds
          setTimeout(() => {
            this.$router.push('/login')
          }, 2000)
        })
        .catch(err => {
          this.error = err.response?.data?.message || 'Registration failed. Please try again.'
        })
        .finally(() => {
          this.loading = false
        })
    }
  }
}
</script>

<style scoped>
.register {
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

.form-label, p, a, .text-danger {
  color: #fff !important;
}

.btn-primary {
  border-radius: 8px;
  height: 48px;
}

a:hover {
  text-decoration: underline;
}

.alert {
    background-color: rgba(0, 0, 0, 0.3);
    border: none;
    color: white;
}
</style>

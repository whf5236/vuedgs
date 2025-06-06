<template>
  <div class="register">
    <div class="row justify-content-center">
      <div class="col-md-6">
        <div class="card shadow">
          <div class="card-body p-5">
            <h2 class="text-center mb-4 text-primary">注册</h2>
            
            <div v-if="error" class="alert alert-danger">
              {{ error }}
            </div>
            
            <div v-if="success" class="alert alert-success">
              {{ success }}
            </div>
            
            <form @submit.prevent="register">
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
                    placeholder="Choose a username"
                  >
                </div>
              </div>
              
              <div class="mb-3">
                <label for="password" class="form-label">密码</label>
                <div class="input-group">
                  <span class="input-group-text"><i class="fas fa-lock"></i></span>
                  <input 
                    type="password" 
                    class="form-control" 
                    id="password" 
                    v-model="password" 
                    required
                    placeholder="Choose a password"
                  >
                </div>
              </div>
              
              <div class="mb-4">
                <label for="confirmPassword" class="form-label">确认密码</label>
                <div class="input-group">
                  <span class="input-group-text"><i class="fas fa-lock"></i></span>
                  <input 
                    type="password" 
                    class="form-control" 
                    id="confirmPassword" 
                    v-model="confirmPassword" 
                    required
                    placeholder="Confirm your password"
                  >
                </div>
                <div v-if="passwordMismatch" class="text-danger mt-1">
                  Passwords do not match
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
              <p>Already have an account? <router-link to="/login">Login</router-link></p>
            </div>
          </div>
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

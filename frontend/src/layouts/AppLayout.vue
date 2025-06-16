<template>
  <div class="app-layout">
    <nav class="navbar navbar-expand-lg modern-navbar">
      <div class="container">
        <router-link class="navbar-brand" to="/">
          <i class="fas fa-cube me-2"></i>
          <span class="fw-bold">3D高斯泼溅全流程训练监控平台</span>
        </router-link>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto align-items-center">
            <template v-if="!isLoggedIn">
              <li class="nav-item">
                <router-link class="nav-link px-3" to="/login">登录</router-link>
              </li>
              <li class="nav-item">
                <router-link class="nav-link px-3" to="/register">注册</router-link>
              </li>
            </template>
            <template v-else>
              <li class="nav-item">
                <router-link class="nav-link px-3" to="/dashboard">主页面</router-link>
              </li>

              <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle user-dropdown" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                  <span class="d-none d-lg-inline me-2">{{ username }}</span>
                  <div class="avatar-circle-small">
                    <span class="avatar-text-small">{{ userInitial }}</span>
                  </div>
                </a>
                <ul class="dropdown-menu dropdown-menu-end shadow-sm" aria-labelledby="userDropdown">
                  <li><router-link class="dropdown-item" to="/dashboard"><i class="fas fa-tachometer-alt fa-sm fa-fw me-2 text-primary-light"></i> 主页面</router-link></li>
                  <li><router-link class="dropdown-item" to="/profile"><i class="fas fa-user fa-sm fa-fw me-2 text-primary-light"></i>个人信息</router-link></li>
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item" href="#" @click.prevent="logout"><i class="fas fa-sign-out-alt fa-sm fa-fw me-2 text-primary-light"></i> 登出</a></li>
                </ul>
              </li>
            </template>
          </ul>
        </div>
      </div>
    </nav>

    <div class="container py-3">
      <router-view />
    </div>

  </div>
</template>

<script>
export default {
  name: 'AppLayout',
  methods: {
    async logout() {
      await this.$store.dispatch('logout');
      this.$router.push('/login');
    }
  },
  computed: {
    isLoggedIn() {
      return this.$store.getters.isAuthenticated;
    },
    username() {
      return this.$store.getters.user?.username || 'User';
    },
    userInitial() {
      return this.username.charAt(0).toUpperCase();
    }
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* The background from AuthLayout will be visible through transparent elements */
}

/* New Glassmorphism Navbar */
.modern-navbar {
  position: relative;
  z-index: 1050;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.navbar-brand,
.nav-link {
  color: #ffffff !important;
  font-weight: 500;
  transition: all 0.2s ease;
  padding: 0.75rem 1rem;
}

.navbar-brand {
  font-size: 1.25rem;
  padding: 0;
}

.nav-link:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  color: #ffffff !important;
}

.text-primary-light {
  color: #a5b4fc !important;
}

/* Avatar styles */
.avatar-circle-small {
  width: 36px;
  height: 36px;
  background-color: rgba(255, 255, 255, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  margin-left: 8px;
  transition: all 0.2s ease;
}

.dropdown-toggle:hover .avatar-circle-small {
  background-color: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

.avatar-text-small {
  font-size: 14px;
  color: white;
  font-weight: bold;
}

/* New Dropdown styles for glass theme */
.dropdown-menu {
  background: rgba(20, 25, 40, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  border-radius: 0.5rem;
  padding: 0.5rem;
  margin-top: 0.5rem;
  min-width: 12rem;
  animation: dropdown-animation 0.2s ease-out;
  z-index: 9999 !important;
  position: absolute;
  color: white;
}

@keyframes dropdown-animation {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-item {
  padding: 0.6rem 1rem;
  font-weight: 500;
  color: #f0f0f0; /* Lighter text for dark transparent background */
  border-radius: 0.35rem;
  margin-bottom: 2px;
  transition: all 0.15s ease;
}

.dropdown-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transform: translateX(3px);
}

.dropdown-item:active {
  background-color: rgba(78, 115, 223, 0.8);
  color: white;
}

.dropdown-divider {
  margin: 0.5rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* Remove unused footer style */
</style>
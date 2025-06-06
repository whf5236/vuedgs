<template>
  <div id="app">
    <Particles
      id="tsparticles"
      :particlesInit="particlesInit"
      :particlesLoaded="particlesLoaded"
      :options="particlesOptions"
      class="particles-bg"
    />

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

    <footer class="mt-5 py-3 text-center footer-modern">
      <div class="container">
        <p class="mb-0">© 2025 高斯泼溅训练平台. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<script>
import { loadFull } from "tsparticles";
import { Particles } from "vue3-particles";

export default {
  name: 'App',
  components: {
    Particles
  },
  data() {
    return {
      particlesOptions: {
        background: {
          color: {
            value: "transparent",
          },
        },
        fpsLimit: 60,
        particles: {
          color: {
            value: "#dedede",
          },
          links: {
            color: "#dedede",
            distance: 150,
            enable: true,
            opacity: 0.4,
            width: 1,
          },
          move: {
            enable: true,
            speed: 3,
          },
          number: {
            value: 80,
            density: {
              enable: true,
              area: 800,
            },
          },
          opacity: {
            value: 0.7,
          },
          shape: {
            type: "circle",
          },
          size: {
            value: 4,
          },
        },
        interactivity: {
          events: {
            onClick: {
              enable: true,
              mode: "push",
            },
            onHover: {
              enable: true,
              mode: "grab",
            },
          },
        },
        detectRetina: true,
      },
    };
  },
  methods: {
    async particlesInit(engine) {
      try {
        // tsparticles v2的加载方式
        await loadFull(engine);
      } catch (error) {
        console.error('Failed to initialize particles:', error);
        // 如果初始化失败，不中断应用其他功能
      }
    },
    particlesLoaded(container) {
      console.log("Particles container loaded", container);
    },
    logout() {
      this.$store.dispatch('logout');
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

<style>
body {
  background-color: #f8f9fa;
  min-height: 100vh;
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

footer {
  margin-top: auto;
}

/* 现代导航栏样式 */
.modern-navbar {
  background: linear-gradient(90deg, #4e73df 0%, #224abe 100%);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 0.75rem 1rem;
}

.navbar-brand {
  font-size: 1.25rem;
  padding: 0;
}

.nav-link {
  font-weight: 500;
  transition: all 0.2s ease;
  padding: 0.75rem 1rem;
}

.nav-link:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
}

.text-primary-light {
  color: #6e8aef !important;
}

/* 小头像样式 */
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

/* 下拉菜单样式 */
.dropdown-menu {
  border: none;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  border-radius: 0.5rem;
  padding: 0.5rem;
  margin-top: 0.5rem;
  min-width: 12rem;
  animation: dropdown-animation 0.2s ease-out;
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
  color: #3a3b45;
  border-radius: 0.35rem;
  margin-bottom: 2px;
  transition: all 0.15s ease;
}

.dropdown-item:hover {
  background-color: #f0f3ff;
  color: #4e73df;
  transform: translateX(3px);
}

.dropdown-item:active {
  background-color: #4e73df;
  color: white;
}

.dropdown-divider {
  margin: 0.5rem 0;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

/* 页脚样式 */
.footer-modern {
  background-color: #f8f9fa;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  color: #6c757d;
  font-size: 0.9rem;
}

.particles-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}
</style>

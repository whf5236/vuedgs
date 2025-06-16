<template>
  <div id="app">
    <Particles
      id="tsparticles"
      :particlesInit="particlesInit"
      :particlesLoaded="particlesLoaded"
      :options="particlesOptions"
      class="particles-bg"
    />
    <component :is="layout" />
  </div>
</template>

<script>
import { loadFull } from "tsparticles";
import AppLayout from './layouts/AppLayout.vue';
import AuthLayout from './layouts/AuthLayout.vue';

export default {
  name: 'App',
  components: {
    AppLayout,
    AuthLayout
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
            value: "#ffffff",
          },
          links: {
            color: "#ffffff",
            distance: 150,
            enable: true,
            opacity: 0.5,
            width: 1,
          },
          collisions: {
            enable: true,
          },
          move: {
            direction: "none",
            enable: true,
            outModes: {
              default: "bounce",
            },
            random: false,
            speed: 2,
            straight: false,
          },
          number: {
            density: {
              enable: true,
              area: 800,
            },
            value: 80,
          },
          opacity: {
            value: 0.5,
          },
          shape: {
            type: "circle",
          },
          size: {
            value: { min: 1, max: 5 },
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
              mode: "repulse",
            },
            resize: true,
          },
          modes: {
            push: {
              quantity: 4,
            },
            repulse: {
              distance: 200,
              duration: 0.4,
            },
          },
        },
        detectRetina: true,
      },
    };
  },
  computed: {
    layout() {
      // 检查路由元信息来决定使用哪个布局
      // 默认为 'AppLayout'
      return this.$route.meta.layout || 'AppLayout';
    }
  },
  methods: {
    async particlesInit(engine) {
      try {
        await loadFull(engine);
      } catch (error) {
        console.error('Failed to initialize particles:', error);
      }
    },
    particlesLoaded(container) {
      console.log("Particles container loaded", container);
    },
  }
}
</script>

<style >
/* Global styles */
body {
  background-color: #f8f9fa;
  min-height: 100vh;
  background-image: url('~@/assets/img/bg.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-attachment: fixed;
}

#app {
  position: relative;
  z-index: 1;
}

.particles-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
}
</style>

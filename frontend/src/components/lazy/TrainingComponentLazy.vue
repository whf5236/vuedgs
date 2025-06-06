<template>
  <div class="training-component-lazy">
    <Suspense>
      <template #default>
        <TrainingComponent />
      </template>
      <template #fallback>
        <div class="loading-container">
          <div class="spinner"></div>
          <p>正在加载训练组件...</p>
        </div>
      </template>
    </Suspense>
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'

const TrainingComponent = defineAsyncComponent(() => 
  import('@/components/TrainingComponent.vue')
)

export default {
  name: 'TrainingComponentLazy',
  components: {
    TrainingComponent
  }
}
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  color: #666;
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border-left-color: #09f;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style> 
<template>
  <div class="home-container">
    <div class="hero-section">
      <h1>3D高斯泼溅全流程训练监控平台</h1>
      <p class="description">一个专业的3D模型训练与监控平台，助力您的项目成功</p>
      
      <div class="action-buttons">
        <button 
          v-if="!isLoggedIn" 
          class="btn btn-primary" 
          @click="$router.push('/login')"
        >
          立即登录
        </button>
        <button 
          v-if="isLoggedIn" 
          class="btn btn-success" 
          @click="$router.push('/dashboard')"
        >
          进入系统
        </button>
      </div>
    </div>

    <div class="features-section">
      <div class="feature-card">
        <div class="feature-icon">📁</div>
        <h3>文件管理</h3>
        <p>简单高效的文件上传与管理系统，支持多种文件格式</p>
      </div>
      
      <div class="feature-card">
        <div class="feature-icon">📊</div>
        <h3>点云处理</h3>
        <p>强大的点云数据处理功能，提高模型训练效率</p>
      </div>
      
      <div class="feature-card">
        <div class="feature-icon">⚙️</div>
        <h3>模型训练</h3>
        <p>多种训练选项，满足各类项目需求</p>
      </div>
      
      <div class="feature-card">
        <div class="feature-icon">📈</div>
        <h3>实时监控</h3>
        <p>训练过程实时可视化，监控模型进展</p>
      </div>
    </div>
  </div>

</template>

<script>
export default {
  name: 'HomePage',
  computed: {
    isLoggedIn() {
      return this.$store.getters.isAuthenticated
    }
  }
}
</script>

<style src="../assets/css/Home.css">

</style>

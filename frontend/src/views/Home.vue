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
  name: 'Home',
  computed: {
    isLoggedIn() {
      return this.$store.getters.isAuthenticated
    }
  }
}
</script>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 20px;
  color: #ffffff;
}

.hero-section {
  text-align: center;
  padding: 60px 40px;
  margin-bottom: 60px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 2.8rem;
  color: #ffffff;
  margin-bottom: 20px;
  font-weight: 700;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

.description {
  font-size: 1.2rem;
  color: #e0e0e0;
  max-width: 700px;
  margin: 0 auto 30px;
  line-height: 1.6;
}

.action-buttons {
  margin-top: 30px;
}

.btn {
  padding: 12px 30px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 30px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin: 0 10px;
}

.btn-primary {
  background-color: #4e73df;
  color: white;
}

.btn-primary:hover {
  background-color: #3a59c7;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(78, 115, 223, 0.25);
}

.btn-success {
  background-color: #1cc88a;
  color: white;
}

.btn-success:hover {
  background-color: #16a173;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(28, 200, 138, 0.25);
}

.features-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  margin-top: 60px;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 30px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  text-align: center;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.15);
}

.feature-icon {
  font-size: 40px;
  margin-bottom: 15px;
}

.feature-card h3 {
  font-size: 1.3rem;
  margin-bottom: 15px;
  color: #ffffff;
}

.feature-card p {
  color: #e0e0e0;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .hero-section {
    padding: 40px 15px;
  }
  
  h1 {
    font-size: 2rem;
  }
  
  .description {
    font-size: 1rem;
  }
}
</style>

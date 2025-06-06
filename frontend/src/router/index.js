import { createRouter, createWebHistory } from 'vue-router'
import Register from '@/views/Register.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/home',
    redirect: '/'
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  // 添加一个捕获所有未匹配路由的路由
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Token验证缓存，避免频繁验证
let tokenValidationCache = {
  token: null,
  isValid: false,
  lastCheck: 0,
  cacheTimeout: 5 * 60 * 1000 // 5分钟缓存
}

// 将缓存暴露到window对象，以便在其他模块中访问
window.tokenValidationCache = tokenValidationCache

// 路由守卫
router.beforeEach(async (to, from, next) => {
  console.log(`[Router] 导航至: ${to.path}`)
  const token = localStorage.getItem('token')
  console.log(`[Router] Token存在: ${!!token}`)
  
  if (to.meta.requiresAuth) {
    console.log(`[Router] 路由需要认证: ${to.path}`)
    if (!token) {
      console.log('[Router] 未找到token，跳转到登录页')
      next('/login')
      return
    }
    
    // 检查缓存是否有效
    const now = Date.now()
    const isCacheValid = tokenValidationCache.token === token && 
                        tokenValidationCache.isValid && 
                        (now - tokenValidationCache.lastCheck) < tokenValidationCache.cacheTimeout
    
    if (isCacheValid) {
      console.log('[Router] 使用缓存的token验证结果')
      next()
      return
    }
    
    // 验证token有效性
    try {
      console.log('[Router] 尝试验证token...')
      const response = await fetch('http://localhost:5000/api/verify-token', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        console.log(`[Router] Token验证失败，响应状态码: ${response.status}`)
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        Object.assign(tokenValidationCache, { token: null, isValid: false, lastCheck: 0, cacheTimeout: 5 * 60 * 1000 })
        next('/login')
        return
      }
      
      const data = await response.json()
      console.log(`[Router] Token验证成功，用户: ${data.username}`)
      
      // Token有效，更新缓存并继续访问
      Object.assign(tokenValidationCache, {
        token: token,
        isValid: true,
        lastCheck: now,
        cacheTimeout: 5 * 60 * 1000
      })
      next()
    } catch (error) {
      console.error('[Router] Token验证失败:', error)
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      Object.assign(tokenValidationCache, { token: null, isValid: false, lastCheck: 0, cacheTimeout: 5 * 60 * 1000 })
      next('/login')
    }
  } else if (to.path === '/login' && token) {
    // 如果用户已登录但访问登录页，重定向到仪表板
    console.log('[Router] 用户已登录，重定向到仪表板')
    next('/dashboard')
  } else {
    // 不需要认证的页面，直接访问
    console.log(`[Router] 访问不需认证的页面: ${to.path}`)
    next()
  }
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue')
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue')
    },
    {
      path: '/config',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue')
    },
    {
      path: '/explore',
      name: 'explorer',
      component: () => import('@/views/FileExplorerView.vue')
    }
  ]
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Public pages that do not require authentication
  const publicPages = ['/login', '/register', '/']
  const authRequired = !publicPages.includes(to.path)
  
  if (authRequired && !authStore.isLoggedIn) {
    return next('/login')
  }
  
  if (authStore.isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    return next('/explore')
  }
  
  next()
})

export default router

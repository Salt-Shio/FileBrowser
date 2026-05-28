import { createRouter, createWebHistory } from 'vue-router'

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

export default router

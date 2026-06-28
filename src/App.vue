<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 使用 Pinia store 的真實登入狀態
const isLoggedIn = computed(() => authStore.isLoggedIn)

const logout = () => {
  authStore.logout()
  router.push('/')
}

// 根據路由名稱來決定要顯示的中文麵包屑
const currentRouteName = computed(() => {
  const nameMap: Record<string, string> = {
    'Home': '主頁',
    'Login': '登入',
    'Register': '註冊',
    'FileExplorer': '檔案系統',
    'Config': '設定',
    'Settings': '設定',
  }
  return route.name && typeof route.name === 'string' ? (nameMap[route.name] || route.name) : ''
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-mono-900 text-mono-50 font-sans selection:bg-mono-500 selection:text-white">
    <!-- Navbar (科技終端機風格) -->
    <nav class="bg-black flex items-center justify-between px-10 py-8 border-b border-mono-700 relative z-20">
      <div class="flex items-center">
        <!-- Logo 結合 Monospace 與閃爍游標 -->
        <router-link to="/" class="text-[55px] font-mono font-bold hover:[text-shadow:0_0_15px_rgba(255,255,255,0.7)] transition-all duration-300 flex items-center">
          <span class="text-mono-500 mr-4 font-normal">&gt;</span>
          <span class="text-mono-50 tracking-tight">Salty File_Explore</span>
          <span class="animate-pulse text-mono-500 ml-1 font-normal">_</span>
        </router-link>
      </div>

      <div class="flex gap-12 items-center">
        <!-- 未登入狀態 -->
        <template v-if="!isLoggedIn">
          <router-link 
            to="/register" 
            class="text-[45px] font-extrabold text-mono-400 hover:text-mono-50 hover:[text-shadow:0_0_15px_rgba(255,255,255,0.7)] transition-all duration-200"
          >
            註冊
          </router-link>
          <router-link 
            to="/login" 
            class="text-[45px] font-extrabold text-mono-400 hover:text-mono-50 hover:[text-shadow:0_0_15px_rgba(255,255,255,0.7)] transition-all duration-200 relative group"
          >
            登入
            <span class="absolute -bottom-2 left-0 w-full h-[2px] bg-mono-50 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left"></span>
          </router-link>
        </template>

        <!-- 已登入狀態 -->
        <template v-else>
          <router-link 
            to="/explore" 
            class="text-[45px] font-extrabold text-mono-400 hover:text-mono-50 hover:[text-shadow:0_0_15px_rgba(255,255,255,0.7)] transition-all duration-200"
          >
            檔案系統
          </router-link>
          <router-link 
            to="/config" 
            class="text-[45px] font-extrabold text-mono-400 hover:text-mono-50 hover:[text-shadow:0_0_15px_rgba(255,255,255,0.7)] transition-all duration-200"
          >
            設定
          </router-link>
          <button 
            @click="logout"
            class="text-[45px] font-extrabold text-mono-400 hover:text-mono-50 hover:[text-shadow:0_0_15px_rgba(255,255,255,0.7)] transition-all duration-200 cursor-pointer"
          >
            登出
          </button>
        </template>
      </div>
    </nav>

    <!-- 麵包屑導航 (Phase 5.2 需求) -->
    <div v-if="route.path !== '/' && currentRouteName" class="bg-mono-900 border-b border-mono-700 px-10 py-4 flex items-center gap-4 relative overflow-hidden z-10">
      <!-- 背景科幻網格點綴 -->
      <div class="absolute inset-0 opacity-[0.04] pointer-events-none" style="background-image: radial-gradient(#fff 1px, transparent 1px); background-size: 20px 20px;"></div>
      
      <p class="font-mono text-[31px] font-bold text-mono-400 flex items-center z-10">
        <router-link to="/" class="hover:text-mono-50 transition-colors">主頁</router-link>
        <span class="mx-4 text-mono-600 font-normal">--&gt;</span>
        <span class="text-mono-50 underline decoration-mono-500 underline-offset-8 [text-shadow:0_0_8px_rgba(255,255,255,0.4)]">
          {{ currentRouteName }}
        </span>
      </p>
    </div>

    <!-- 頁面主體 -->
    <main class="flex-grow bg-mono-900 relative">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

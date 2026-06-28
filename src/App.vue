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
    <nav class="bg-black flex items-center justify-between px-8 py-5 border-b border-mono-700 relative z-20">
      <div class="flex items-center">
        <!-- Logo 結合 Monospace 與閃爍游標 -->
        <router-link to="/" class="text-4xl font-mono font-bold hover:text-white transition-all duration-300 flex items-center group">
          <span class="text-mono-500 mr-4 font-normal group-hover:text-mono-400">&gt;</span>
          <span class="text-mono-200 tracking-wider uppercase group-hover:text-white group-hover:[text-shadow:0_0_15px_rgba(255,255,255,0.4)]">Salty_File_Explore</span>
          <span class="animate-terminal-blink ml-1 font-normal">_</span>
        </router-link>
      </div>

      <div class="flex gap-10 items-center font-mono text-2xl tracking-widest">
        <!-- 未登入狀態 -->
        <template v-if="!isLoggedIn">
          <router-link 
            to="/register" 
            class="text-mono-400 hover:text-white transition-all duration-200 flex items-center gap-2 group"
          >
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">[</span>
            註冊
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">]</span>
          </router-link>
          <router-link 
            to="/login" 
            class="text-mono-400 hover:text-white transition-all duration-200 flex items-center gap-2 group"
          >
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">[</span>
            登入
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">]</span>
          </router-link>
        </template>

        <!-- 已登入狀態 -->
        <template v-else>
          <router-link 
            to="/explore" 
            class="text-mono-400 hover:text-white transition-all duration-200 flex items-center gap-2 group"
          >
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">[</span>
            檔案系統
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">]</span>
          </router-link>
          <router-link 
            to="/config" 
            class="text-mono-400 hover:text-white transition-all duration-200 flex items-center gap-2 group"
          >
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">[</span>
            設定
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">]</span>
          </router-link>
          <button 
            @click="logout"
            class="text-mono-400 hover:text-white transition-all duration-200 flex items-center gap-2 group cursor-pointer"
          >
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">[</span>
            登出
            <span class="text-mono-700 group-hover:text-mono-400 transition-colors">]</span>
          </button>
        </template>
      </div>
    </nav>

    <!-- 麵包屑導航 (Phase 5.2 需求) -->
    <div v-if="route.path !== '/' && currentRouteName" class="bg-mono-900 border-b border-mono-800 px-10 py-3 flex items-center gap-4 relative overflow-hidden z-10">
      <!-- 背景科幻網格點綴 -->
      <div class="absolute inset-0 opacity-[0.04] pointer-events-none" style="background-image: radial-gradient(#fff 1px, transparent 1px); background-size: 20px 20px;"></div>
      
      <p class="font-mono text-xl tracking-widest text-mono-400 flex items-center z-10">
        <router-link to="/" class="hover:text-white transition-colors">主頁</router-link>
        <span class="mx-4 text-mono-600 font-normal">/</span>
        <span class="text-mono-100 font-bold">
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

@keyframes terminal-blink {
  0%, 100% { 
    opacity: 1; 
    color: #fff;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
  }
  50% { 
    opacity: 0; 
  }
}

.animate-terminal-blink {
  animation: terminal-blink 1s step-end infinite;
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 使用 Pinia store 的真實登入狀態
const isLoggedIn = computed(() => authStore.isLoggedIn)

const logout = () => {
  authStore.logout()
  router.push('/')
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-mono-500 text-mono-50">
    <!-- Navbar (基於 Figma Node 12:10) -->
    <nav class="bg-black flex items-center justify-between px-10 py-8 border-b border-mono-800">
      <div class="flex items-center">
        <router-link to="/" class="text-4xl font-bold hover:text-mono-200 transition-colors">
          &gt; Salty File_Explore
        </router-link>
      </div>

      <div class="flex gap-12 items-center">
        <!-- 未登入狀態 -->
        <template v-if="!isLoggedIn">
          <router-link 
            to="/register" 
            class="text-3xl font-extrabold opacity-60 hover:opacity-100 transition-opacity"
          >
            註冊
          </router-link>
          <router-link 
            to="/login" 
            class="text-3xl font-extrabold hover:text-mono-200 drop-shadow-md transition-all"
          >
            登入
          </router-link>
        </template>

        <!-- 已登入狀態 -->
        <template v-else>
          <router-link 
            to="/explore" 
            class="text-3xl font-extrabold hover:text-mono-200 transition-all"
          >
            檔案系統
          </router-link>
          <router-link 
            to="/config" 
            class="text-3xl font-extrabold hover:text-mono-200 transition-all"
          >
            設定
          </router-link>
          <button 
            @click="logout"
            class="text-3xl font-extrabold opacity-60 hover:opacity-100 transition-opacity"
          >
            登出
          </button>
        </template>
      </div>
    </nav>

    <!-- 頁面主體 -->
    <main class="flex-grow">
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

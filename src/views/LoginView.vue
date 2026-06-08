<script setup lang="ts">
import { ref, reactive, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import BaseCard from '@/components/ui/BaseCard.vue';
import BaseInput from '@/components/ui/BaseInput.vue';
import BaseButton from '@/components/ui/BaseButton.vue';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

// 登入階段狀態控制: 'PASSWORD' (第一階段) | 'OTP' (第二階段)
const stage = ref<'PASSWORD' | 'OTP'>('PASSWORD');

const form = reactive({
  username: '',
  password: '',
});

const otpCode = ref('');
const errorMessage = ref<string | null>(null);
const isLoading = ref(false);

// 密碼登入提交
const handleLoginSubmit = async () => {
  if (!form.username || !form.password) {
    errorMessage.value = '請輸入使用者名稱與密碼';
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;

  try {
    const result = await authStore.login({
      username: form.username,
      password: form.password,
    });

    if (result.require2FA) {
      stage.value = 'OTP';
      otpCode.value = '';
    } else {
      // 登入成功，直接導向首頁/檔案總管
      router.push('/explore');
    }
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || '登入失敗，請檢查您的帳號與密碼';
  } finally {
    isLoading.value = false;
  }
};

// 2FA OTP 驗證提交
const handleOTPVerifySubmit = async () => {
  if (!otpCode.value || otpCode.value.length !== 6) {
    errorMessage.value = '請輸入 6 位數安全驗證碼';
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;

  try {
    await authStore.verify2FA(otpCode.value);
    router.push('/explore');
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || '驗證碼錯誤或已過期，請重新輸入';
  } finally {
    isLoading.value = false;
  }
};

// 返回第一階段
const handleBackToPassword = () => {
  stage.value = 'PASSWORD';
  otpCode.value = '';
  errorMessage.value = null;
};
</script>

<template>
  <div class="flex flex-col items-center justify-center pt-20 px-4">
    <transition name="fade" mode="out-in">
      <!-- 2FA OTP 驗證階段 -->
      <BaseCard v-if="stage === 'OTP'" key="otp-card">
        <template #header>
          <h2 class="text-3xl font-medium text-white">雙重驗證 (2FA)</h2>
        </template>
        
        <div class="flex flex-col gap-6 w-full text-black">
          <!-- 錯誤訊息提示 -->
          <div v-if="errorMessage" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
            {{ errorMessage }}
          </div>

          <div class="text-center px-2">
            <p class="text-xl font-bold mb-2">安全金鑰驗證</p>
            <p class="text-mono-600 text-base leading-relaxed">
              您的帳號已啟用 2FA 安全鎖保護。<br>請輸入您 Authenticator App 中的 6 位數驗證碼。
            </p>
          </div>

          <BaseInput 
            v-model="otpCode"
            label="驗證碼"
            placeholder="000000"
            maxlength="6"
            :disabled="isLoading"
            @keyup.enter="handleOTPVerifySubmit"
          />

          <div class="mt-4 flex flex-col gap-4">
            <BaseButton 
              @click="handleOTPVerifySubmit" 
              :loading="isLoading"
              class="w-full text-xl py-4"
            >
              驗證並登入
            </BaseButton>

            <button 
              @click="handleBackToPassword" 
              :disabled="isLoading"
              class="text-mono-600 hover:text-black font-semibold transition-colors text-center text-sm py-2 disabled:opacity-50"
            >
              返回輸入密碼
            </button>
          </div>
        </div>
      </BaseCard>

      <!-- 密碼登入第一階段 -->
      <BaseCard v-else key="password-card">
        <template #header>
          <h2 class="text-3xl font-medium text-white">安全登入入口</h2>
        </template>

        <div class="flex flex-col gap-6 w-full">
          <!-- 錯誤訊息提示 -->
          <div v-if="errorMessage" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
            {{ errorMessage }}
          </div>

          <BaseInput 
            v-model="form.username"
            label="使用者名稱"
            placeholder="輸入使用者名稱"
            :disabled="isLoading"
            @keyup.enter="handleLoginSubmit"
          />

          <BaseInput 
            v-model="form.password"
            label="密碼"
            type="password"
            placeholder="輸入您的密碼"
            :disabled="isLoading"
            @keyup.enter="handleLoginSubmit"
          />

          <div class="mt-4">
            <BaseButton 
              @click="handleLoginSubmit" 
              :loading="isLoading"
              class="w-full text-xl py-4"
            >
              安全登入
            </BaseButton>
            
            <router-link 
              to="/register" 
              class="text-mono-600 hover:text-black font-semibold transition-colors text-center block text-sm mt-6"
            >
              尚未註冊？建立新帳號
            </router-link>
          </div>
        </div>
      </BaseCard>
    </transition>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: scale(0.98);
}
.fade-leave-to {
  opacity: 0;
  transform: scale(1.02);
}
</style>

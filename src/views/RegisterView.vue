<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import BaseCard from '@/components/ui/BaseCard.vue';
import BaseInput from '@/components/ui/BaseInput.vue';
import BaseButton from '@/components/ui/BaseButton.vue';
import BaseModal from '@/components/ui/BaseModal.vue';
import { RegisterValidator } from '@/utils/validators';
import { useAuthStore } from '@/stores/auth';
import type { RegisterFormState } from '@/types/auth';

const router = useRouter();
const authStore = useAuthStore();

// State Machine Stages: 'FORM' | 'LEGAL' | 'SUCCESS'
const stage = ref<'FORM' | 'LEGAL' | 'SUCCESS'>('FORM');

const form = reactive<RegisterFormState>({
  username: '',
  password: '',
  confirmPassword: '',
});

const errorMessage = ref<string | null>(null);
const isLoading = ref(false);

const handleRegisterClick = () => {
  errorMessage.value = RegisterValidator.validate(form);
  if (!errorMessage.value) {
    stage.value = 'LEGAL';
  }
};

const handleLegalDecline = () => {
  stage.value = 'FORM';
};

const handleLegalAccept = async () => {
  stage.value = 'FORM'; // Back to form to show loading on the button
  isLoading.value = true;
  errorMessage.value = null;

  try {
    await authStore.register({
      username: form.username,
      password: form.password,
    });
    stage.value = 'SUCCESS';
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || '註冊失敗，請稍後再試';
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="flex flex-col items-center justify-start pt-8 px-4 w-full min-h-full">
    <!-- Success State -->
    <BaseCard v-if="stage === 'SUCCESS'">
      <template #header>
        <h2 class="text-3xl font-medium text-white">註冊成功</h2>
      </template>
      <div class="flex flex-col items-center gap-6 py-4">
        <div class="bg-mono-50 rounded-full p-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p class="text-xl text-mono-50 text-center font-medium">您的帳號已成功建立！</p>
        <BaseButton @click="router.push('/login')" class="w-full">
          前往登入
        </BaseButton>
      </div>
    </BaseCard>

    <!-- Form Input Stage -->
    <BaseCard v-else>
      <template #header>
        <h2 class="text-3xl font-medium text-white">註冊新帳號</h2>
      </template>
      
      <div class="flex flex-col gap-6 w-full">
        <!-- Error Message -->
        <div v-if="errorMessage" class="bg-red-500/20 border border-red-500 text-red-100 p-3 rounded-lg text-sm text-center">
          {{ errorMessage }}
        </div>

        <BaseInput 
          v-model="form.username"
          label="使用者名稱"
          placeholder="輸入使用者名稱"
          :disabled="isLoading"
        />

        <BaseInput 
          v-model="form.password"
          label="密碼"
          type="password"
          placeholder="輸入密碼"
          :disabled="isLoading"
        />

        <BaseInput 
          v-model="form.confirmPassword"
          label="再次輸入密碼"
          type="password"
          placeholder="再次輸入密碼"
          :disabled="isLoading"
        />

        <div class="mt-4">
          <BaseButton 
            @click="handleRegisterClick" 
            :loading="isLoading"
            class="w-full text-xl py-4"
          >
            註冊
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <!-- Legal Modal (Stage 2) -->
    <BaseModal 
      v-if="stage === 'LEGAL'" 
      title="法律條款" 
      @close="handleLegalDecline"
    >
      <div class="max-w-none text-white text-lg">
        <p class="mb-4">歡迎使用 Salty File Explorer。在您開始使用本服務前，請仔細閱讀以下條款：</p>
        <ul class="list-decimal pl-6 flex flex-col gap-3">
          <li>本服務僅供合法用途使用。</li>
          <li>使用者對其上傳的任何內容負全部法律責任。</li>
          <li>我們保留隨時更新本條款的權利。</li>
          <li>您的隱私對我們非常重要，相關資料將受到嚴格保護。</li>
        </ul>
        <p class="mt-6 italic opacity-70 text-sm">點擊「同意」即代表您已閱讀並接受以上所有條款。</p>
      </div>
      <template #footer>
        <div class="flex gap-4">
          <BaseButton variant="white" @click="handleLegalDecline" class="flex-1">
            不同意
          </BaseButton>
          <BaseButton @click="handleLegalAccept" class="flex-1">
            同意
          </BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>

<template>
  <BaseModal v-if="isOpen" title="Two-Factor Authentication" @close="close">
    <div class="flex flex-col items-center w-full">
      <div class="flex flex-col gap-6 items-center w-full">
        <p class="text-mono-300 font-mono text-sm text-center">
          請使用 Google Authenticator 等 App 掃描以下 QR Code 綁定
        </p>

        <!-- QR Code 區塊 -->
        <div class="bg-white p-3 rounded-xl shadow-[0_0_15px_rgba(255,255,255,0.2)]">
           <qrcode-vue :value="provisioningUri" :size="200" level="M" v-if="provisioningUri" />
        </div>
        
        <!-- 金鑰顯示區塊 -->
        <div class="bg-mono-950 border border-mono-700 p-3 rounded-lg w-full text-center shadow-inner">
          <p class="font-mono text-sm text-mono-400 break-all select-all cursor-text">
            Key: <span class="text-mono-50 font-bold">{{ secret }}</span>
          </p>
        </div>
        
        <!-- 驗證碼輸入區 -->
        <div class="w-full mt-2 flex flex-col gap-4 border-t border-mono-800 pt-6">
          <BaseInput 
            v-model="otpCode" 
            label="OTP 驗證碼"
            placeholder="請輸入 6 位數驗證碼"
            @keyup.enter="handleEnable"
          />
          <div class="flex gap-3">
            <BaseButton variant="ghost" class="flex-1 text-sm py-2.5 border border-mono-700 hover:bg-mono-800 text-mono-200" @click="close">
              取消
            </BaseButton>
            <BaseButton class="flex-1 text-sm py-2.5 bg-mono-50 text-black hover:bg-mono-200 shadow-[0_0_10px_rgba(255,255,255,0.2)]" @click="handleEnable" :disabled="!otpCode || loading">
              {{ loading ? 'VERIFYING...' : 'CONFIRM' }}
            </BaseButton>
          </div>
        </div>
        
        <p v-if="error" class="text-red-400 font-mono text-sm bg-red-900/20 px-4 py-2 rounded border border-red-900/30 w-full text-center mt-2">{{ error }}</p>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import QrcodeVue from 'qrcode.vue';
import { useAuthStore } from '@/stores/auth';
import BaseModal from '@/components/ui/BaseModal.vue';
import BaseInput from '@/components/ui/BaseInput.vue';
import BaseButton from '@/components/ui/BaseButton.vue';

const props = defineProps<{
  isOpen: boolean;
  secret: string;
  provisioningUri: string;
}>();

const emit = defineEmits(['close', 'success']);
const authStore = useAuthStore();

const otpCode = ref('');
const loading = ref(false);
const error = ref('');

function close() {
  otpCode.value = '';
  error.value = '';
  emit('close');
}

async function handleEnable() {
  if (!otpCode.value) return;
  
  loading.value = true;
  error.value = '';
  try {
    await authStore.enable2FA(otpCode.value);
    emit('success');
    close();
  } catch (e: any) {
    error.value = e.response?.data?.detail || '驗證失敗，請檢查驗證碼是否正確';
  } finally {
    loading.value = false;
  }
}
</script>

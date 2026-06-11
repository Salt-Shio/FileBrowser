<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-[#7b7b7b] flex flex-col gap-2.5 items-center pb-2.5 relative rounded-[25px] w-full max-w-md">
      <!-- Header -->
      <div class="bg-[#3b3b3b] flex h-[72px] items-center justify-center py-2.5 relative rounded-t-[25px] w-full shrink-0">
        <h2 class="font-medium text-[30px] text-white text-center">請掃描 QRcode 綁定</h2>
        <button @click="close" class="absolute right-4 top-4 text-white text-3xl font-bold">&times;</button>
      </div>
      
      <!-- Content -->
      <div class="flex flex-col gap-[15px] items-center p-4 w-full shrink-0">
        <div class="bg-white p-2 border-4 border-black rounded-lg shrink-0">
           <qrcode-vue :value="provisioningUri" :size="250" level="M" v-if="provisioningUri" />
        </div>
        
        <div class="bg-[#383838] flex items-center justify-center p-2.5 rounded-[10px] w-full shrink-0">
          <p class="font-medium text-lg text-white text-center break-all">
            金鑰: {{ secret }}
          </p>
        </div>
        
        <div class="flex flex-col gap-4 py-2.5 w-full shrink-0">
          <div class="bg-[#a8a8a8] border-4 border-black flex items-center justify-center p-2 rounded-[20px] w-full">
            <input 
              v-model="otpCode" 
              type="text" 
              placeholder="請輸入 OTP"
              class="bg-transparent text-white placeholder-gray-200 outline-none w-full text-2xl text-center"
              @keyup.enter="handleEnable"
            />
          </div>
          <button 
            @click="handleEnable"
            :disabled="!otpCode || loading"
            class="bg-black text-white font-bold py-3 rounded-[20px] text-2xl hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {{ loading ? '驗證中...' : '確認綁定' }}
          </button>
        </div>
        
        <p v-if="error" class="text-red-300 font-bold text-center">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import QrcodeVue from 'qrcode.vue';
import { useAuthStore } from '@/stores/auth';

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

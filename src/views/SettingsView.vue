<template>
  <div class="bg-[#707070] min-h-screen relative w-full overflow-x-hidden">
    <!-- Main Content -->
    <div class="flex flex-col items-center justify-center mt-12 mb-20 w-full px-4">
      <div class="flex flex-col gap-10 w-full max-w-4xl items-center">
        <!-- Settings Form -->
        <div class="flex flex-col md:flex-row w-full gap-2 md:gap-0">
          <!-- Labels -->
          <div class="flex flex-col gap-4 md:w-1/3 shrink-0">
            <div class="bg-[#adadad] border-4 border-black flex items-center justify-center p-3 md:rounded-l-[15px] md:rounded-r-none rounded-[15px] h-[62px]">
              <p class="font-medium text-[#474747] text-2xl text-center">使用者名稱</p>
            </div>
            <div class="bg-[#adadad] border-4 border-black flex items-center justify-center p-3 md:rounded-l-[15px] md:rounded-r-none rounded-[15px] h-[62px]">
              <p class="font-medium text-[#474747] text-2xl text-center">更改密碼</p>
            </div>
            <div class="bg-[#adadad] border-4 border-black flex items-center justify-center p-3 md:rounded-l-[15px] md:rounded-r-none rounded-[15px] h-[62px]">
              <p class="font-medium text-[#474747] text-2xl text-center">確認密碼</p>
            </div>
          </div>
          
          <!-- Inputs -->
          <div class="flex flex-col gap-4 md:w-2/3 flex-grow">
            <div class="bg-white border-4 border-[#504c4c] flex items-center px-4 md:rounded-r-[15px] md:rounded-l-none rounded-[15px] h-[62px]">
              <input type="text" :value="authStore.user?.username" disabled class="w-full h-full outline-none font-medium text-xl text-[#adadad] bg-transparent" placeholder="請輸入新使用者名稱" />
            </div>
            <div class="bg-white border-4 border-[#504c4c] flex items-center px-4 md:rounded-r-[15px] md:rounded-l-none rounded-[15px] h-[62px]">
              <input type="password" v-model="newPassword" class="w-full h-full outline-none font-medium text-xl text-black bg-transparent" placeholder="請輸入新密碼" />
            </div>
            <div class="bg-white border-4 border-[#504c4c] flex items-center px-4 md:rounded-r-[15px] md:rounded-l-none rounded-[15px] h-[62px]">
              <input type="password" v-model="confirmPassword" class="w-full h-full outline-none font-medium text-xl text-black bg-transparent" placeholder="請確認新密碼" />
            </div>
          </div>
        </div>

        <!-- Confirm Button -->
        <div class="w-full flex justify-center mt-4">
          <button @click="handleSaveConfig" class="bg-black hover:bg-gray-800 transition-colors flex items-center justify-center p-3 rounded-[20px] w-full max-w-sm h-[62px]">
            <p class="font-medium text-3xl text-white text-center">確認</p>
          </button>
        </div>

        <!-- 2FA Button -->
        <div class="mt-8 flex flex-col items-center gap-4">
           <button v-if="!is2FAEnabled" @click="open2FAModal" :disabled="generating2FA" class="bg-[#a8a8a8] hover:bg-gray-400 transition-colors flex items-center justify-center px-8 py-4 rounded-[20px]">
              <p class="font-medium text-3xl text-white text-center">{{ generating2FA ? '產生中...' : '啟用 2FA' }}</p>
           </button>
           <button v-else @click="handleDisable2FA" class="bg-red-800 hover:bg-red-700 transition-colors flex items-center justify-center px-8 py-4 rounded-[20px]">
              <p class="font-medium text-3xl text-white text-center">停用 2FA</p>
           </button>
           <p v-if="errorMsg" class="text-red-300 font-bold">{{ errorMsg }}</p>
        </div>
      </div>
    </div>

    <!-- 2FA Modal -->
    <TwoFactorEnableModal 
      :is-open="show2FAModal"
      :secret="twoFaSecret"
      :provisioning-uri="twoFaUri"
      @close="show2FAModal = false"
      @success="handle2FASuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import TwoFactorEnableModal from '@/components/auth/TwoFactorEnableModal.vue';

const authStore = useAuthStore();

const newPassword = ref('');
const confirmPassword = ref('');

const show2FAModal = ref(false);
const generating2FA = ref(false);
const twoFaSecret = ref('');
const twoFaUri = ref('');
const errorMsg = ref('');

const is2FAEnabled = computed(() => authStore.user?.is_totp_enabled || false);

function handleSaveConfig() {
  console.log('Save config clicked (Not implemented in backend yet)', {
    newPassword: newPassword.value,
    confirmPassword: confirmPassword.value
  });
  alert('設定功能尚未實作後端 API');
}

async function open2FAModal() {
  errorMsg.value = '';
  generating2FA.value = true;
  try {
    const data = await authStore.generate2FA();
    twoFaSecret.value = data.secret;
    twoFaUri.value = data.provisioning_uri;
    show2FAModal.value = true;
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '產生 2FA 金鑰失敗';
  } finally {
    generating2FA.value = false;
  }
}

function handle2FASuccess() {
  alert('2FA 綁定成功！下次登入將會要求輸入驗證碼。');
}

async function handleDisable2FA() {
  const code = prompt('請輸入目前的 2FA 驗證碼以停用：');
  if (!code) return;
  
  try {
    await authStore.disable2FA(code);
    alert('2FA 已成功停用！');
  } catch (e: any) {
    alert(e.response?.data?.detail || '停用失敗，驗證碼錯誤');
  }
}
</script>

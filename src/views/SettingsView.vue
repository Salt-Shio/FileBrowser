<template>
  <div class="min-h-full relative w-full overflow-x-hidden pt-8">
    <!-- Main Content -->
    <div class="flex flex-col items-center justify-start mt-12 mb-20 w-full px-4">
      <div class="flex flex-col gap-10 w-full max-w-4xl items-center bg-mono-950/50 p-12 rounded-xl border border-mono-700 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
        
        <h2 class="text-2xl font-mono text-mono-50 font-bold w-full border-b border-mono-800 pb-4 mb-4 [text-shadow:0_0_8px_rgba(255,255,255,0.2)]">System / Settings</h2>

        <!-- Settings Form -->
        <div class="flex flex-col w-full gap-6">
          
          <!-- Username (Readonly) -->
          <div class="flex flex-col md:flex-row gap-4 items-start md:items-center w-full">
            <div class="md:w-[200px] shrink-0 font-mono text-sm text-mono-300 flex items-center">
              <span class="mr-2 text-mono-500">&gt;</span> 使用者名稱
            </div>
            <div class="flex-grow w-full bg-mono-900 border border-mono-700 rounded-lg h-[45px] px-4 flex items-center shadow-inner">
              <input type="text" :value="authStore.user?.username" disabled class="w-full bg-transparent outline-none font-mono text-sm text-mono-500" />
            </div>
          </div>

          <!-- Old Password -->
          <div class="flex flex-col md:flex-row gap-4 items-start md:items-center w-full">
            <div class="md:w-[200px] shrink-0 font-mono text-sm text-mono-300 flex items-center">
              <span class="mr-2 text-mono-500">&gt;</span> 目前密碼
            </div>
            <div class="flex-grow w-full bg-mono-950 border border-mono-700 rounded-lg h-[45px] px-4 flex items-center shadow-inner focus-within:border-mono-500 focus-within:shadow-[0_0_8px_rgba(255,255,255,0.1)] transition-all">
              <input type="password" v-model="oldPassword" class="w-full bg-transparent outline-none font-mono text-sm text-mono-50 placeholder-mono-600" placeholder="請輸入目前密碼" />
            </div>
          </div>

          <!-- New Password -->
          <div class="flex flex-col md:flex-row gap-4 items-start md:items-center w-full">
            <div class="md:w-[200px] shrink-0 font-mono text-sm text-mono-300 flex items-center">
              <span class="mr-2 text-mono-500">&gt;</span> 更改密碼
            </div>
            <div class="flex-grow w-full bg-mono-950 border border-mono-700 rounded-lg h-[45px] px-4 flex items-center shadow-inner focus-within:border-mono-500 focus-within:shadow-[0_0_8px_rgba(255,255,255,0.1)] transition-all">
              <input type="password" v-model="newPassword" class="w-full bg-transparent outline-none font-mono text-sm text-mono-50 placeholder-mono-600" placeholder="請輸入新密碼" />
            </div>
          </div>

          <!-- Confirm Password -->
          <div class="flex flex-col md:flex-row gap-4 items-start md:items-center w-full">
            <div class="md:w-[200px] shrink-0 font-mono text-sm text-mono-300 flex items-center">
              <span class="mr-2 text-mono-500">&gt;</span> 確認密碼
            </div>
            <div class="flex-grow w-full bg-mono-950 border border-mono-700 rounded-lg h-[45px] px-4 flex items-center shadow-inner focus-within:border-mono-500 focus-within:shadow-[0_0_8px_rgba(255,255,255,0.1)] transition-all">
              <input type="password" v-model="confirmPassword" class="w-full bg-transparent outline-none font-mono text-sm text-mono-50 placeholder-mono-600" placeholder="請確認新密碼" />
            </div>
          </div>

        </div>

        <!-- Confirm Button -->
        <div class="w-full flex justify-end mt-4 pt-6 border-t border-mono-800">
          <button @click="handleSaveConfig" class="bg-mono-50 hover:bg-white text-mono-900 transition-colors flex items-center justify-center px-8 py-2.5 rounded-md font-bold text-sm shadow-[0_0_15px_rgba(255,255,255,0.2)] active:scale-95">
            確認修改
          </button>
        </div>

        <!-- 2FA Button -->
        <div class="mt-4 flex flex-col items-center gap-4 w-full border-t border-mono-800 pt-8">
           <div class="w-full flex flex-col md:flex-row justify-between items-center bg-mono-900/50 p-6 rounded-lg border border-mono-700 gap-4">
             <div class="flex flex-col gap-1 w-full text-center md:text-left">
               <span class="font-mono text-mono-50 font-bold">Two-Factor Authentication (2FA)</span>
               <span class="font-mono text-mono-400 text-xs">增強帳戶安全性，登入時需輸入動態驗證碼。</span>
             </div>
             <button v-if="!is2FAEnabled" @click="open2FAModal" :disabled="generating2FA" class="shrink-0 bg-mono-800 hover:bg-mono-700 text-mono-50 transition-colors flex items-center justify-center px-6 py-2 rounded-md font-bold text-sm border border-mono-600 shadow-sm active:scale-95 disabled:opacity-50">
                {{ generating2FA ? 'GENERATING...' : 'ENABLE 2FA' }}
             </button>
             <button v-else @click="handleDisable2FA" class="shrink-0 bg-red-900/40 hover:bg-red-900/60 text-red-400 border border-red-900/50 transition-colors flex items-center justify-center px-6 py-2 rounded-md font-bold text-sm shadow-sm active:scale-95">
                DISABLE 2FA
             </button>
           </div>
           <p v-if="errorMsg" class="text-red-400 font-mono text-sm bg-red-900/20 px-4 py-2 rounded border border-red-900/30 w-full text-center">{{ errorMsg }}</p>
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
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');

const show2FAModal = ref(false);
const generating2FA = ref(false);
const twoFaSecret = ref('');
const twoFaUri = ref('');
const errorMsg = ref('');

const is2FAEnabled = computed(() => authStore.user?.is_totp_enabled || false);

async function handleSaveConfig() {
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    alert('請填寫所有密碼欄位');
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    alert('新密碼與確認密碼不一致');
    return;
  }

  try {
    await authStore.changePassword(oldPassword.value, newPassword.value);
    alert('密碼修改成功，請重新登入！');
    authStore.logout();
    router.push('/login');
  } catch (e: any) {
    alert(e.response?.data?.detail || '密碼修改失敗');
  }
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

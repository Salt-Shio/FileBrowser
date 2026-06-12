import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authApi } from '@/api/auth';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null);
  const token = ref<string>(localStorage.getItem('token') || '');
  const twoFaToken = ref<string>('');
  const username = ref<string>('');

  const isLoggedIn = computed(() => !!token.value);

  async function register(payload: any) {
    const response = await authApi.register(payload);
    return response.data;
  }

  async function login(payload: any) {
    const response = await authApi.login(payload);
    const data = response.data;

    if (data.require_2fa) {
      twoFaToken.value = data.two_fa_token || '';
      username.value = data.username || '';
      return { require2FA: true };
    } else {
      token.value = data.access_token || '';
      localStorage.setItem('token', token.value);
      username.value = data.username || '';
      await fetchUserProfile();
      return { require2FA: false };
    }
  }

  async function verify2FA(otpCode: string) {
    if (!twoFaToken.value) {
      throw new Error('2FA 驗證流程未初始化，請重新登入');
    }
    const response = await authApi.verify2FA({
      two_fa_token: twoFaToken.value,
      otp_code: otpCode
    });
    const data = response.data;
    token.value = data.access_token || '';
    localStorage.setItem('token', token.value);
    twoFaToken.value = '';
    await fetchUserProfile();
  }

  async function fetchUserProfile() {
    if (!token.value) return;
    try {
      const response = await authApi.getMe();
      user.value = response.data;
    } catch (error) {
      logout();
      throw error;
    }
  }

  async function generate2FA() {
    const response = await authApi.generate2FA();
    return response.data; // { secret, provisioning_uri }
  }

  async function enable2FA(otpCode: string) {
    const response = await authApi.enable2FA({ otp_code: otpCode });
    // update user state
    await fetchUserProfile();
    return response.data;
  }

  async function disable2FA(otpCode: string) {
    const response = await authApi.disable2FA({ otp_code: otpCode });
    // update user state
    await fetchUserProfile();
    return response.data;
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    const response = await authApi.changePassword({ 
      old_password: oldPassword, 
      new_password: newPassword 
    });
    return response.data;
  }

  function logout() {
    user.value = null;
    token.value = '';
    twoFaToken.value = '';
    username.value = '';
    localStorage.removeItem('token');
  }

  // Automatically fetch profile if token exists on load
  if (token.value && !user.value) {
    fetchUserProfile().catch(() => { });
  }

  return {
    user,
    token,
    twoFaToken,
    username,
    isLoggedIn,
    register,
    login,
    verify2FA,
    generate2FA,
    enable2FA,
    disable2FA,
    changePassword,
    fetchUserProfile,
    logout
  };
});

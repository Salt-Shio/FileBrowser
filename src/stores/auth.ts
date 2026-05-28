import { defineStore } from 'pinia';
import { ref } from 'vue';
import { authApi } from '@/api/auth';

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null);
  const token = ref(localStorage.getItem('token') || '');

  async function register(payload: any) {
    const response = await authApi.register(payload);
    // Note: register in the backend returns UserResponse (User object)
    return response.data;
  }

  return {
    user,
    token,
    register
  };
});

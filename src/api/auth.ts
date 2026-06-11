import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to automatically attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const authApi = {
  register(payload: any) {
    return api.post('/auth/register', payload);
  },
  login(payload: any) {
    return api.post('/auth/login', payload);
  },
  verify2FA(payload: { two_fa_token: string; otp_code: string }) {
    return api.post('/auth/verify-2fa', payload);
  },
  getMe() {
    return api.get('/auth/me');
  },
  generate2FA() {
    return api.post('/auth/2fa/generate');
  },
  enable2FA(payload: { otp_code: string }) {
    return api.post('/auth/2fa/enable', payload);
  },
  disable2FA(payload: { otp_code: string }) {
    return api.post('/auth/2fa/disable', payload);
  },
};

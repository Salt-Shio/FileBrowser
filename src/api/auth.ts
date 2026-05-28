import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const authApi = {
  register(payload: any) {
    return api.post('/auth/register', payload);
  },
  login(payload: any) {
    return api.post('/auth/login', payload);
  },
};

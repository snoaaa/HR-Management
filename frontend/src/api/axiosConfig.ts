import axios from 'axios';
import { API_URL } from './baseUrl';

const getBaseApiUrl = (): string => {
  let url = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/';
  url = url.trim();
  if (!url.endsWith('/')) {
    url += '/';
  }
  if (!url.includes('/api/')) {
    url = `${url.replace(/\/+$/, '')}/api/`;
  }
  return url;
};

const API_BASE_URL = getBaseApiUrl();

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If error is 401 and it's not a retry or a login/refresh request
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url.includes('login') && !originalRequest.url.includes('refresh')) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          // Attempt to refresh the token
          const res = await axios.post(`${API_URL}auth/refresh/`, {
            refresh: refreshToken
          });
          
          if (res.status === 200) {
            localStorage.setItem('access_token', res.data.access);
            // Optionally, update refresh token if rotation is enabled
            if (res.data.refresh) {
              localStorage.setItem('refresh_token', res.data.refresh);
            }
            
            // Retry the original request with new token
            originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          // Refresh failed, session is truly inactive/expired
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/signin';
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token, logout immediately
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/signin';
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;

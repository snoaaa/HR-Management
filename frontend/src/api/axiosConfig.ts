import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/', // Assuming Django runs on 8000
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
    // Handling automatic logout on 401 when not trying to login/refresh
    if (error.response?.status === 401 && !error.config.url.includes('login')) {
      // BN-174: automatic closing of inactive session
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/signin';
    }
    return Promise.reject(error);
  }
);

export default api;

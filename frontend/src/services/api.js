import axios from 'axios';
import { useAuthStore } from '../stores/authStore';
import useCompanyStore from '../stores/useCompanyStore';
import { useNotificationStore } from '../stores/notificationStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  const companyId = useCompanyStore.getState().companyId;
  if (companyId !== null && companyId !== undefined && !config.headers['X-Company-Id']) {
    config.headers['X-Company-Id'] = companyId.toString();
  }
  
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Network Error',
        message: 'Unable to connect to the server. Please check your internet connection.'
      });
      return Promise.reject(error);
    }
    
    const { status, data } = error.response;
    
    switch (status) {
      case 401:
        useAuthStore.getState().logout();
        window.location.href = '/login';
        break;
      case 403:
        useNotificationStore.getState().addNotification({
          type: 'error',
          title: 'Access Denied',
          message: data.detail || 'You do not have permission to perform this action.'
        });
        break;
      case 400:
      case 422:
      case 409:
        useNotificationStore.getState().addNotification({
          type: 'warning',
          title: 'Validation Error',
          message: data.detail || 'Please check your inputs and try again.'
        });
        break;
      case 500:
        console.error('System Error:', error);
        useNotificationStore.getState().addNotification({
          type: 'error',
          title: 'System Error',
          message: 'An unexpected error occurred. Our team has been notified.'
        });
        break;
      default:
        break;
    }
    return Promise.reject(error);
  }
);

export default api;

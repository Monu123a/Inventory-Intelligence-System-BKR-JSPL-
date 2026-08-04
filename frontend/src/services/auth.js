import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const login = async (credentials) => {
  try {
    const response = await api.post(API_ROUTES.AUTH.LOGIN, credentials);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getMe = async () => {
  try {
    const response = await api.get(API_ROUTES.AUTH.ME);
    return response.data;
  } catch (error) {
    throw error;
  }
};

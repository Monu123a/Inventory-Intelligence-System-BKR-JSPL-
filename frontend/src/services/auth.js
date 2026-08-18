import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const authService = {
  login: async (credentials) => {
    const response = await api.post(API_ROUTES.AUTH.LOGIN, credentials);
    return normalizeResponse(response.data);
  },

  getMe: async () => {
    const response = await api.get(API_ROUTES.AUTH.ME);
    return normalizeResponse(response.data);
  }
};

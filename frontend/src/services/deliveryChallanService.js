import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const deliveryChallanService = {
  createChallan: async (payload) => {
    const response = await api.post(`${API_ROUTES.DELIVERY_CHALLANS}/`, payload);
    return normalizeResponse(response.data);
  },

  getAllChallans: async () => {
    const response = await api.get(`${API_ROUTES.DELIVERY_CHALLANS}/`);
    return normalizeResponse(response.data);
  },

  getChallanById: async (id) => {
    const response = await api.get(`${API_ROUTES.DELIVERY_CHALLANS}/${id}`);
    return normalizeResponse(response.data);
  },

  printChallan: async (id) => {
    const response = await api.post(`${API_ROUTES.DELIVERY_CHALLANS}/${id}/print`);
    return normalizeResponse(response.data);
  },

  cancelChallan: async (id) => {
    const response = await api.post(`${API_ROUTES.DELIVERY_CHALLANS}/${id}/cancel`);
    return normalizeResponse(response.data);
  },
};

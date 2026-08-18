import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const amazonReturnsService = {
  getReturns: async (params = {}) => {
    const response = await api.get(`${API_ROUTES.AMAZON_RETURNS}/`, { params });
    return normalizeResponse(response.data);
  },

  getSyncStatus: async () => {
    const response = await api.get(`${API_ROUTES.AMAZON_RETURNS}/status`);
    return normalizeResponse(response.data);
  },

  triggerSync: async () => {
    const response = await api.post(`${API_ROUTES.AMAZON_RETURNS}/sync`);
    return normalizeResponse(response.data);
  },

  inspectReturn: async (returnId, payload) => {
    const response = await api.post(`${API_ROUTES.AMAZON_RETURNS}/${returnId}/inspect`, payload);
    return normalizeResponse(response.data);
  },
};

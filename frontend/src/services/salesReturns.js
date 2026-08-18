import api from './api';
import { normalizeResponse } from '../utils/normalizeResponse';

export const salesReturnsService = {
  getReturns: async () => {
    const response = await api.get('/api/sales-returns/');
    return normalizeResponse(response.data);
  },
  completeReturn: async (id) => {
    const response = await api.post(`/api/sales-returns/${id}/complete`);
    return normalizeResponse(response.data);
  },
  cancelReturn: async (id) => {
    const response = await api.post(`/api/sales-returns/${id}/cancel`);
    return normalizeResponse(response.data);
  }
};

import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const amazonService = {
  getLiveInventory: async () => {
    const response = await api.get(`${API_ROUTES.AMAZON}/live-inventory`);
    return normalizeResponse(response.data);
  },

  getSyncStatus: async () => {
    const response = await api.get(`${API_ROUTES.AMAZON}/sync-status`);
    return normalizeResponse(response.data);
  },

  triggerSync: async (params = {}) => {
    const response = await api.post(`${API_ROUTES.AMAZON}/sync`, null, { params });
    return normalizeResponse(response.data);
  },

  getDlqRecords: async (limit = 50) => {
    const response = await api.get(`${API_ROUTES.AMAZON}/dlq`, { params: { limit } });
    return normalizeResponse(response.data);
  },

  requestFcShipments: async (params = {}) => {
    const response = await api.post(`${API_ROUTES.AMAZON}/request-fc-shipments`, null, { params });
    return normalizeResponse(response.data);
  },

  uploadFcShipments: async (formData) => {
    const response = await api.post(`${API_ROUTES.AMAZON}/upload-fc-shipments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return normalizeResponse(response.data);
  },

  getFcInventorySummary: async () => {
    const response = await api.get(`${API_ROUTES.AMAZON}/fc-inventory-summary`);
    return normalizeResponse(response.data);
  },
};

import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const stateHubService = {
  getAll: async () => {
    const response = await api.get(`${API_ROUTES.STATE_HUBS}/`);
    return normalizeResponse(response.data);
  },

  create: async (payload) => {
    const response = await api.post(`${API_ROUTES.STATE_HUBS}/`, payload);
    return normalizeResponse(response.data);
  },

  update: async (id, payload) => {
    const response = await api.put(`${API_ROUTES.STATE_HUBS}/${id}`, payload);
    return normalizeResponse(response.data);
  },

  delete: async (id) => {
    const response = await api.delete(`${API_ROUTES.STATE_HUBS}/${id}`);
    return normalizeResponse(response.data);
  },
};

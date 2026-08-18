import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const dashboardService = {
  getMetrics: async () => {
    const response = await api.get(API_ROUTES.DASHBOARD.METRICS);
    return normalizeResponse(response.data);
  },

  getActivity: async () => {
    const response = await api.get(API_ROUTES.DASHBOARD.ACTIVITY);
    return normalizeResponse(response.data);
  },

  getAlerts: async () => {
    const response = await api.get(API_ROUTES.DASHBOARD.ALERTS);
    return normalizeResponse(response.data);
  },

  resolveAlert: async (alertId) => {
    const response = await api.put(`${API_ROUTES.DASHBOARD.ALERTS}/${alertId}/resolve`);
    return normalizeResponse(response.data);
  }
};

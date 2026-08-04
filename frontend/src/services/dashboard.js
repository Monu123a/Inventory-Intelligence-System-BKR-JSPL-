import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const getMetrics = async () => {
  const response = await api.get(API_ROUTES.DASHBOARD.METRICS);
  return response.data;
};

export const getActivity = async () => {
  const response = await api.get(API_ROUTES.DASHBOARD.ACTIVITY);
  return response.data;
};

export const getAlerts = async () => {
  const response = await api.get(API_ROUTES.DASHBOARD.ALERTS);
  return response.data;
};

export const resolveAlert = async (alertId) => {
  const response = await api.put(`${API_ROUTES.DASHBOARD.ALERTS}/${alertId}/resolve`);
  return response.data;
};

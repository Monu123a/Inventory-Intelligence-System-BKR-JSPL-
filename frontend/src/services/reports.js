import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const generateLowStockReport = async (format = 'excel') => {
  const response = await api.post(`${API_ROUTES.REPORTS.LOW_STOCK}?format=${format}`);
  return response.data;
};

export const generateNegativeStockReport = async (format = 'excel') => {
  const response = await api.post(`${API_ROUTES.REPORTS.NEGATIVE_STOCK}?format=${format}`);
  return response.data;
};

export const generateReplenishmentReport = async (format = 'excel') => {
  const response = await api.post(`${API_ROUTES.REPORTS.REPLENISHMENT}?format=${format}`);
  return response.data;
};

export const getReportHistory = async (reportType) => {
  const params = reportType ? { report_type: reportType } : {};
  const response = await api.get(API_ROUTES.REPORTS.HISTORY, { params });
  return response.data;
};

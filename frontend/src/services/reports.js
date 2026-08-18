import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const reportsService = {
  generateLowStock: async (format = 'excel') => {
    const response = await api.post(`${API_ROUTES.REPORTS.LOW_STOCK}?format=${format}`);
    return normalizeResponse(response.data);
  },
  generateNegativeStock: async (format = 'excel') => {
    const response = await api.post(`${API_ROUTES.REPORTS.NEGATIVE_STOCK}?format=${format}`);
    return normalizeResponse(response.data);
  },
  generateReplenishment: async (format = 'excel') => {
    const response = await api.post(`${API_ROUTES.REPORTS.REPLENISHMENT}?format=${format}`);
    return normalizeResponse(response.data);
  },
  getHistory: async (reportType) => {
    const params = reportType ? { report_type: reportType } : {};
    const response = await api.get(API_ROUTES.REPORTS.HISTORY, { params });
    return normalizeResponse(response.data);
  },
  getInventoryReport: async (params) => {
    const response = await api.get('/api/business-reports/inventory', { params });
    return normalizeResponse(response.data);
  },
  getAmazonReturns: async () => {
    const response = await api.get('/api/reports/returns/amazon-returns');
    return normalizeResponse(response.data);
  },
  getDefectiveInventory: async () => {
    const response = await api.get('/api/reports/returns/defective-inventory');
    return normalizeResponse(response.data);
  },
  getSalesReport: async (params) => {
    const response = await api.get('/api/business-reports/sales', { params });
    return normalizeResponse(response.data);
  },
  getDispatchReport: async (params) => {
    const response = await api.get('/api/business-reports/dispatches', { params });
    return normalizeResponse(response.data);
  },
  getFCReturnsReport: async (params) => {
    const response = await api.get('/api/business-reports/returns', { params });
    return normalizeResponse(response.data);
  },
  getDefectiveReport: async (params) => {
    const response = await api.get('/api/business-reports/defective', { params });
    return normalizeResponse(response.data);
  },
  getReturnsMetrics: async () => {
    const response = await api.get('/api/reports/returns/metrics');
    return normalizeResponse(response.data);
  },
  downloadReport: (endpoint) => {
    window.open(endpoint, '_blank');
  }
};

import api from './api';
import { normalizeResponse } from '../utils/normalizeResponse';

export const bkrService = {
  createJobCard: async (data) => {
    const response = await api.post('/api/bkr-services/job-cards', data);
    return normalizeResponse(response.data);
  },
  getJobCards: async () => {
    const response = await api.get('/api/bkr-services/job-cards');
    return normalizeResponse(response.data);
  },
  getJobCard: async (id) => {
    const response = await api.get(`/api/bkr-services/job-cards/${id}`);
    return normalizeResponse(response.data);
  },
  updateJobCardStatus: async (id, status) => {
    const response = await api.patch(`/api/bkr-services/job-cards/${id}/status`, { status });
    return normalizeResponse(response.data);
  },
  createServiceInvoice: async (data) => {
    const response = await api.post('/api/bkr-services/invoices', data);
    return normalizeResponse(response.data);
  },
  getServiceInvoices: async () => {
    const response = await api.get('/api/bkr-services/invoices');
    return normalizeResponse(response.data);
  },
  getServiceInvoice: async (id) => {
    const response = await api.get(`/api/bkr-services/invoices/${id}`);
    return normalizeResponse(response.data);
  }
};

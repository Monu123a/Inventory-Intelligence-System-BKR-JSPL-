import api from './api';
import { normalizeResponse } from '../utils/normalizeResponse';

export const posService = {
  cancelSale: async (saleId) => {
    const response = await api.post(`/pos/sales/${saleId}/cancel`);
    return response.data;
  },

  searchProducts: async (query, warehouseId) => {
    if (!query || query.length < 2) return [];
    let url = `/api/pos/products/search?q=${encodeURIComponent(query)}`;
    if (warehouseId) url += `&warehouse_id=${warehouseId}`;
    const res = await api.get(url);
    return normalizeResponse(res.data);
  },

  checkout: async (payload) => {
    const res = await api.post('/api/pos/sale', payload);
    return normalizeResponse(res.data);
  },

  getSalesHistory: async (params) => {
    const res = await api.get('/api/pos/history', { params });
    return normalizeResponse(res.data);
  },

  getSaleById: async (saleId) => {
    const res = await api.get(`/api/pos/sales/${saleId}`);
    return normalizeResponse(res.data);
  },

  retryTallySync: async (saleId) => {
    const res = await api.post(`/api/pos/sales/${saleId}/retry-tally`);
    return normalizeResponse(res.data);
  },

  getTallyPayload: async (saleId) => {
    const res = await api.get(`/api/pos/sales/${saleId}/tally-payload`);
    return normalizeResponse(res.data);
  },

  emailInvoice: async ({ saleId, formData }) => {
    const res = await api.post(`/api/documents/invoice/${saleId}/email`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return normalizeResponse(res.data);
  },

  // --- Offline POS Queue ---
  submitOffline: async (payload, idempotencyKey) => {
    const res = await api.post('/api/pos/offline/submit', {
      idempotency_key: idempotencyKey,
      payload
    });
    return normalizeResponse(res.data);
  },

  getPending: async () => {
    const res = await api.get('/api/pos/offline/pending');
    return normalizeResponse(res.data);
  },

  syncOffline: async () => {
    const res = await api.post('/api/pos/offline/sync');
    return normalizeResponse(res.data);
  }
};

import api from './api';

export const einvoiceService = {
  getSettings: async () => {
    const res = await api.get('/api/einvoice/settings');
    return res.data;
  },

  updateSettings: async (data) => {
    const res = await api.put('/api/einvoice/settings', data);
    return res.data;
  },

  generateIRN: async (saleId, forceRetry = false) => {
    const res = await api.post(`/api/einvoice/generate/${saleId}?force_retry=${forceRetry}`);
    return res.data;
  },

  cancelIRN: async (saleId, cancelReason = '1', remarks = 'Cancelled by user') => {
    const res = await api.post(`/api/einvoice/cancel/${saleId}`, {
      cancel_reason: cancelReason,
      remarks: remarks
    });
    return res.data;
  },

  getStatus: async (saleId) => {
    const res = await api.get(`/api/einvoice/status/${saleId}`);
    return res.data;
  }
};

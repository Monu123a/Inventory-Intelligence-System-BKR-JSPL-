import api from './api';

const OFFLINE_KEY = 'offlinePurchases';

export const PurchaseService = {
  // Save locally if offline
  queueOfflineSubmit: (payload, idempotencyKey) => {
    let queue = JSON.parse(localStorage.getItem(OFFLINE_KEY) || '[]');
    queue.push({ payload, idempotencyKey, timestamp: new Date().toISOString() });
    localStorage.setItem(OFFLINE_KEY, JSON.stringify(queue));
    return { status: 'PENDING', message: 'Saved offline' };
  },

  getOfflineQueue: () => {
    return JSON.parse(localStorage.getItem(OFFLINE_KEY) || '[]');
  },

  clearOfflineQueue: () => {
    localStorage.removeItem(OFFLINE_KEY);
  },

  // API Calls
  createDraft: async (data) => {
    if (!navigator.onLine) {
      return PurchaseService.queueOfflineSubmit(data, data.idempotency_key);
    }
    const response = await api.post('/api/purchases', data);
    return response.data;
  },

  receivePurchase: async (purchaseId, data) => {
    const response = await api.post(`/api/purchases/${purchaseId}/receive`, data);
    return response.data;
  },

  syncOffline: async (companyId) => {
    const queue = PurchaseService.getOfflineQueue();
    if (queue.length === 0) return { synced: 0, details: [] };
    
    // Push them to the backend offline queue first
    for (let item of queue) {
      try {
        await api.post('/api/purchases/offline/submit', {
          idempotency_key: item.idempotencyKey,
          ...item.payload
        });
      } catch (e) {
        console.error("Failed to submit offline item to server", e);
      }
    }
    PurchaseService.clearOfflineQueue();

    // Now trigger the server sync job
    const response = await api.post(`/api/purchases/offline/sync?company_id=${companyId}`);
    return response.data;
  },

  
  getPurchases: async () => {
    const response = await api.get('/api/purchases');
    return response.data;
  },

  getPurchaseById: async (purchaseId) => {
    const response = await api.get(`/api/purchases/${purchaseId}`);
    return response.data;
  },

  recordPayment: async (purchaseId, data) => {
    const response = await api.post(`/api/purchases/${purchaseId}/pay`, data);
    return response.data;
  },

  getPayables: async (companyId) => {
    const response = await api.get(`/api/purchases/vendors/payables?company_id=${companyId}`);
    return response.data;
  }
};

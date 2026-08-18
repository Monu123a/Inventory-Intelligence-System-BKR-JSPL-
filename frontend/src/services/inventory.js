import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const inventoryService = {
  getInventory: async (params = {}) => {
    // Allows passing { warehouse_id: 1 } via params
    const response = await api.get(`${API_ROUTES.INVENTORY.BASE}/`, { params });
    return normalizeResponse(response.data);
  },

  getInventoryHistory: async (sku) => {
    const response = await api.get(`${API_ROUTES.INVENTORY.BASE}/${sku}/history`);
    return normalizeResponse(response.data);
  },

  getGlobalInventoryHistory: async () => {
    const response = await api.get(API_ROUTES.INVENTORY.HISTORY);
    return normalizeResponse(response.data);
  },

  uploadInventory: async ({ warehouseCode, uploadType, file, preview = false }) => {
    const formData = new FormData();
    formData.append('warehouse_code', warehouseCode);
    formData.append('upload_type', uploadType);
    formData.append('preview', preview);
    formData.append('file', file);
    
    const response = await api.post(API_ROUTES.INVENTORY.UPLOAD, formData, {
      transformRequest: [(data, headers) => {
        delete headers['Content-Type'];
        return data;
      }]
    });
    return normalizeResponse(response.data);
  },

  adjustInventory: async (data) => {
    const response = await api.post(`${API_ROUTES.INVENTORY.BASE}/adjust`, data);
    return normalizeResponse(response.data);
  }
};

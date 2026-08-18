import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const warehouseInventoryService = {
  getInventory: async (params = {}) => {
    const response = await api.get(`${API_ROUTES.WAREHOUSE_INVENTORY}/`, { params });
    return normalizeResponse(response.data);
  },
};

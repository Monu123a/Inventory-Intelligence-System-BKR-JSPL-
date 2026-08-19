import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const warehouseService = {
  getWarehouses: async () => {
    const response = await api.get(`${API_ROUTES.WAREHOUSES}/`);
    return normalizeResponse(response.data);
  },

  getWarehouseById: async (id) => {
    const response = await api.get(`${API_ROUTES.WAREHOUSES}/${id}`);
    return normalizeResponse(response.data);
  },

  createWarehouse: async (warehouseData) => {
    const response = await api.post(`${API_ROUTES.WAREHOUSES}/`, warehouseData);
    return normalizeResponse(response.data);
  },

  updateWarehouse: async (id, warehouseData) => {
    const response = await api.put(`${API_ROUTES.WAREHOUSES}/${id}`, warehouseData);
    return normalizeResponse(response.data);
  },

  deleteWarehouse: async (id, adminPassword) => {
    const response = await api.delete(`${API_ROUTES.WAREHOUSES}/${id}`, {
      data: { admin_password: adminPassword }
    });
    return normalizeResponse(response.data);
  },

  getWarehouseUsers: async (warehouseId) => {
    const response = await api.get(`${API_ROUTES.WAREHOUSES}/${warehouseId}/users`);
    return normalizeResponse(response.data);
  },

  assignWarehouseUser: async (warehouseId, userData) => {
    const response = await api.post(`${API_ROUTES.WAREHOUSES}/${warehouseId}/users`, userData);
    return normalizeResponse(response.data);
  },

  removeWarehouseUser: async (warehouseId, userId) => {
    const response = await api.delete(`${API_ROUTES.WAREHOUSES}/${warehouseId}/users/${userId}`);
    return normalizeResponse(response.data);
  }
};

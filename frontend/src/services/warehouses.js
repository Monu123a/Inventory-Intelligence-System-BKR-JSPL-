import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const getWarehouses = async () => {
  const response = await api.get(`${API_ROUTES.WAREHOUSES}/`);
  return response.data;
};

export const createWarehouse = async (warehouseData) => {
  const response = await api.post(`${API_ROUTES.WAREHOUSES}/`, warehouseData);
  return response.data;
};

export const updateWarehouse = async (id, warehouseData) => {
  const response = await api.put(`${API_ROUTES.WAREHOUSES}/${id}`, warehouseData);
  return response.data;
};

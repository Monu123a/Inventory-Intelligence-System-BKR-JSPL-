import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const getInventory = async (warehouseId = null) => {
  const url = warehouseId ? `${API_ROUTES.INVENTORY.BASE}/?warehouse_id=${warehouseId}` : `${API_ROUTES.INVENTORY.BASE}/`;
  const response = await api.get(url);
  return response.data;
};

export const getInventoryHistory = async (sku) => {
  const response = await api.get(`${API_ROUTES.INVENTORY.BASE}/${sku}/history`);
  return response.data;
};

export const getGlobalInventoryHistory = async () => {
  const response = await api.get(API_ROUTES.INVENTORY.HISTORY);
  return response.data;
};

export const uploadInventory = async (warehouseCode, uploadType, file, preview = false) => {
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
  return response.data;
};

export const adjustInventory = async (data) => {
  const response = await api.post(`${API_ROUTES.INVENTORY.BASE}/adjust`, data);
  return response.data;
};

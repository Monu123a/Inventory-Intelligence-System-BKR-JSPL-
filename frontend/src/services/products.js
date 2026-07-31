import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const getProducts = async (params) => {
  const response = await api.get(API_ROUTES.PRODUCTS, { params });
  return response.data;
};

export const getProductFilters = async () => {
  const response = await api.get(`${API_ROUTES.PRODUCTS}/filters`);
  return response.data;
};

export const getProduct = async (sku) => {
  const response = await api.get(`${API_ROUTES.PRODUCTS}/${sku}`);
  return response.data;
};

export const createProduct = async (data) => {
  const response = await api.post(API_ROUTES.PRODUCTS, data);
  return response.data;
};

export const updateProduct = async (sku, data) => {
  const response = await api.put(`${API_ROUTES.PRODUCTS}/${sku}`, data);
  return response.data;
};

export const deleteProduct = async (sku) => {
  const response = await api.delete(`${API_ROUTES.PRODUCTS}/${sku}`);
  return response.data;
};

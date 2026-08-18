import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const productService = {
  getProducts: async () => {
    const response = await api.get(API_ROUTES.PRODUCTS);
    return normalizeResponse(response.data);
  },

  getProductFilters: async () => {
    const response = await api.get(`${API_ROUTES.PRODUCTS}/filters`);
    return normalizeResponse(response.data);
  },

  getProduct: async (sku) => {
    const response = await api.get(`${API_ROUTES.PRODUCTS}/${sku}`);
    return normalizeResponse(response.data);
  },

  createProduct: async (data) => {
    const response = await api.post(API_ROUTES.PRODUCTS, data);
    return normalizeResponse(response.data);
  },

  updateProduct: async (sku, data) => {
    const response = await api.put(`${API_ROUTES.PRODUCTS}/${sku}`, data);
    return normalizeResponse(response.data);
  },

  deleteProduct: async (sku) => {
    const response = await api.delete(`${API_ROUTES.PRODUCTS}/${sku}`);
    return normalizeResponse(response.data);
  }
};

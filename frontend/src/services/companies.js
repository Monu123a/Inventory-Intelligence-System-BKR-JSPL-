import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const companyService = {
  getCompanies: async () => {
    try {
      const response = await api.get(`${API_ROUTES.COMPANIES}/`);
      return normalizeResponse(response.data);
    } catch (error) {
      console.error("Error fetching companies:", error);
      throw error;
    }
  }
};

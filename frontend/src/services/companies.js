import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';

export const getCompanies = async () => {
  try {
    const response = await api.get(`${API_ROUTES.COMPANIES}/`);
    console.log("Companies fetched:", response.data);
    return response.data;
  } catch (error) {
    console.error("Error fetching companies:", error);
    throw error;
  }
};

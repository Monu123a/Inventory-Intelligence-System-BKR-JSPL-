import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const transferService = {
  approveTransfer: async (id) => {
    // Assuming the backend has this endpoint for approving transfers
    const response = await api.post(`/api/logistics/transfers/${id}/approve`);
    return normalizeResponse(response.data);
  }
};

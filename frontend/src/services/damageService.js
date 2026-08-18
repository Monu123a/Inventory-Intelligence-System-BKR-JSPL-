import api from './api';
import { API_ROUTES } from '../constants/apiRoutes';
import { normalizeResponse } from '../utils/normalizeResponse';

export const damageService = {
  createClaim: async (payload) => {
    const response = await api.post(`${API_ROUTES.DAMAGE_CLAIMS}/`, payload);
    return normalizeResponse(response.data);
  },

  updateClaimStatus: async (claimId, status) => {
    const response = await api.patch(`${API_ROUTES.DAMAGE_CLAIMS}/${claimId}/status`, { status });
    return normalizeResponse(response.data);
  },

  getClaims: async (params = {}) => {
    const response = await api.get(`${API_ROUTES.DAMAGE_CLAIMS}/`, { params });
    return normalizeResponse(response.data);
  },
};

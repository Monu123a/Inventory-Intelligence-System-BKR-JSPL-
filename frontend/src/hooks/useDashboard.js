import useCompanyStore from '../stores/useCompanyStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMetrics, getActivity, getAlerts, resolveAlert } from '../services/dashboard';
import { useNotificationStore } from '../stores/notificationStore';
import api from '../services/api';

export const useDashboardMetrics = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  return useQuery({
    queryKey: ['dashboard', 'metrics', companyId],
    queryFn: getMetrics,
    refetchInterval: 60000, // 60s
  });
};

export const useReturnMetrics = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  return useQuery({
    queryKey: ['dashboard', 'returns', companyId],
    queryFn: async () => {
        const res = await api.get('/api/reports/returns/metrics'); // TODO: Move to apiRoutes.js
        return res.data;
    },
    refetchInterval: 60000,
  });
};

export const useDashboardActivity = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  return useQuery({
    queryKey: ['dashboard', 'activity', companyId],
    queryFn: getActivity,
    refetchInterval: 30000, // 30s
  });
};

export const useDashboardAlerts = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  return useQuery({
    queryKey: ['dashboard', 'alerts', companyId],
    queryFn: getAlerts,
    refetchInterval: 15000, // 15s
  });
};

export const useResolveAlert = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: resolveAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'alerts', companyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics', companyId] });
      addNotification({
        type: 'success',
        title: 'Alert Resolved',
        message: 'The alert has been successfully marked as resolved.'
      });
    },
    onError: () => {
      addNotification({
        type: 'error',
        title: 'Resolution Failed',
        message: 'Could not resolve the alert. Please try again.'
      });
    }
  });
};

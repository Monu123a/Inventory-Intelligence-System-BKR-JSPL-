import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import useCompanyStore from '../stores/useCompanyStore';
import { useNotificationStore } from '../stores/notificationStore';

export const useUsers = () => {
  const companyId = useCompanyStore(state => state.companyId);

  return useQuery({
    queryKey: ['users', companyId],
    queryFn: async () => {
      const response = await api.get('/api/users');
      return response.data;
    },
    enabled: !!companyId
  });
};

export const useCreateUser = () => {
  const companyId = useCompanyStore(state => state.companyId);
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore(state => state.addNotification);

  return useMutation({
    mutationFn: async ({ userData, adminPassword }) => {
      const response = await api.post('/api/users', { ...userData, admin_password: adminPassword });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', companyId] });
      addNotification({ type: 'success', title: 'User Created', message: 'Technician was added successfully.' });
    },
    onError: (error) => {
      addNotification({ 
        type: 'error', 
        title: 'Error', 
        message: error.response?.data?.detail || 'Failed to create user' 
      });
    }
  });
};

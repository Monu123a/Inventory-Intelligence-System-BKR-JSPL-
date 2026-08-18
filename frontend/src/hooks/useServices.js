import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { bkrService } from '../services/serviceModule';
import { useNotificationStore } from '../stores/notificationStore';

export const useJobCards = () => {
  return useQuery({
    queryKey: ['job-cards'],
    queryFn: () => bkrService.getJobCards(),
  });
};

export const useJobCard = (id) => {
  return useQuery({
    queryKey: ['job-cards', id],
    queryFn: () => bkrService.getJobCard(id),
    enabled: !!id,
  });
};

export const useCreateJobCard = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: (data) => bkrService.createJobCard(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-cards'] });
      addNotification({ type: 'success', title: 'Success', message: 'Job Card created successfully' });
    },
    onError: (error) => {
      addNotification({ type: 'error', title: 'Error', message: error.message || 'Failed to create Job Card' });
    }
  });
};

export const useUpdateJobCardStatus = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: ({ id, status }) => bkrService.updateJobCardStatus(id, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['job-cards'] });
      queryClient.invalidateQueries({ queryKey: ['job-cards', variables.id] });
      addNotification({ type: 'success', title: 'Success', message: 'Job Card status updated' });
    },
    onError: (error) => {
      addNotification({ type: 'error', title: 'Error', message: error.message || 'Failed to update status' });
    }
  });
};

export const useServiceInvoices = () => {
  return useQuery({
    queryKey: ['service-invoices'],
    queryFn: () => bkrService.getServiceInvoices(),
  });
};

export const useServiceInvoice = (id) => {
  return useQuery({
    queryKey: ['service-invoices', id],
    queryFn: () => bkrService.getServiceInvoice(id),
    enabled: !!id,
  });
};

export const useCreateServiceInvoice = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: (data) => bkrService.createServiceInvoice(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-invoices'] });
      queryClient.invalidateQueries({ queryKey: ['job-cards'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      addNotification({ type: 'success', title: 'Success', message: 'Service Invoice generated successfully' });
    },
    onError: (error) => {
      addNotification({ type: 'error', title: 'Error', message: error.message || 'Failed to generate invoice' });
    }
  });
};

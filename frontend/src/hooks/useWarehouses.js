import useCompanyStore from '../stores/useCompanyStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { warehouseService } from '../services/warehouse';
import { inventoryService } from '../services/inventory';
import { useNotificationStore } from '../stores/notificationStore';
import { useMemo } from 'react';
import api from '../services/api';

const EMPTY_ARRAY = [];

export const useWarehouses = ({ search = '', statusFilter = '', page = 1, limit = 15 } = {}) => {
  const companyId = useCompanyStore((state) => state.companyId);
  const whQuery = useQuery({
    queryKey: ['warehouses', companyId],
    queryFn: () => warehouseService.getWarehouses(),
  });

  const invQuery = useQuery({
    queryKey: ['inventory', 'all', companyId],
    queryFn: () => inventoryService.getInventory(null), // Fetch all inventory
  });

  const rawWarehouses = whQuery.data ?? EMPTY_ARRAY;
  const inventory = invQuery.data ?? EMPTY_ARRAY;

  const processedData = useMemo(() => {
    // 1. Join with Inventory to calculate operational summary
    let joined = rawWarehouses.map(wh => {
      const whInventory = inventory.filter(inv => inv.warehouse_id === wh.id);
      
      const totalProducts = new Set(whInventory.map(inv => inv.product?.sku)).size;
      const totalInventoryQty = whInventory.reduce((sum, inv) => sum + (inv.available_qty || 0), 0);

      return {
        ...wh,
        total_products: totalProducts,
        total_inventory: totalInventoryQty
      };
    });

    // 2. Global Search (Name, Code, Contact Person, Address)
    if (search) {
      const lowerSearch = search.toLowerCase();
      joined = joined.filter(wh => 
        (wh.name || '').toLowerCase().includes(lowerSearch) ||
        (wh.code || '').toLowerCase().includes(lowerSearch) ||
        (wh.contact_person || '').toLowerCase().includes(lowerSearch) ||
        (wh.address || '').toLowerCase().includes(lowerSearch)
      );
    }

    // 3. Status Filter
    if (statusFilter) {
      joined = joined.filter(wh => wh.status === statusFilter);
    }

    // Sort alphabetically by name
    joined.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

    // 4. Pagination
    const startIndex = (page - 1) * limit;
    const paginated = joined.slice(startIndex, startIndex + limit);

    return {
      data: paginated,
      totalCount: joined.length,
      totalPages: Math.ceil(joined.length / limit)
    };
  }, [rawWarehouses, inventory, search, statusFilter, page, limit]);

  return {
    isPending: whQuery.isPending || invQuery.isPending,
    error: whQuery.error || invQuery.error,
    refetch: () => { whQuery.refetch(); invQuery.refetch(); },
    ...processedData
  };
};

export const useCreateWarehouse = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: async ({ data, adminPassword }) => {
      const response = await api.post('/api/warehouses', { ...data, admin_password: adminPassword });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses', companyId] });
      addNotification({ type: 'success', title: 'Warehouse Created', message: `${data.name} was successfully created.` });
    },
    onError: (err) => {
      addNotification({ type: 'error', title: 'Creation Failed', message: err.response?.data?.detail || err.message || 'An error occurred.' });
    }
  });
};

export const useUpdateWarehouse = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: ({ id, data }) => warehouseService.updateWarehouse(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses', companyId] });
      addNotification({ type: 'success', title: 'Warehouse Updated', message: `${data.name} was successfully updated.` });
    },
    onError: (err) => {
      addNotification({ type: 'error', title: 'Update Failed', message: err.response?.data?.detail || err.message || 'An error occurred.' });
    }
  });
};

export const useDeactivateWarehouse = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: ({ id, data }) => warehouseService.updateWarehouse(id, { ...data, status: data.status === 'Active' ? 'Inactive' : 'Active' }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses', companyId] });
      addNotification({ 
        type: 'success', 
        title: 'Status Changed', 
        message: `${data.name} is now ${data.status}.` 
      });
    },
    onError: (err) => {
      addNotification({ type: 'error', title: 'Status Change Failed', message: err.response?.data?.detail || err.message || 'An error occurred.' });
    }
  });
};

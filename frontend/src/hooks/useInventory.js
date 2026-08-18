import useCompanyStore from '../stores/useCompanyStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryService } from '../services/inventory';
import { productService } from '../services/products';
import { warehouseService } from '../services/warehouse';
import { useNotificationStore } from '../stores/notificationStore';
import { handleApiError } from '../utils/errorHandler';
import { useMemo } from 'react';
import api from '../services/api';

const EMPTY_ARRAY = [];

export const useInventory = ({ search = '', warehouseId = '', filterStatus = '', page = 1, limit = 15 }) => {
  const companyId = useCompanyStore((state) => state.companyId);
  const invQuery = useQuery({
    queryKey: ['inventory', warehouseId, companyId],
    queryFn: () => inventoryService.getInventory(warehouseId || null),
  });

  const prodQuery = useQuery({
    queryKey: ['products', companyId],
    queryFn: () => productService.getProducts(),
    enabled: !!companyId,
  });

  const whQuery = useQuery({
    queryKey: ['warehouses', companyId],
    queryFn: () => warehouseService.getWarehouses(),
  });

  const rawInventory = invQuery.data ?? EMPTY_ARRAY;
  const products = prodQuery.data ?? EMPTY_ARRAY;
  const warehouses = whQuery.data ?? EMPTY_ARRAY;

  // Build dynamic warehouse lookup
  const warehouseMap = useMemo(() => {
    const map = {};
    warehouses.forEach(wh => { map[wh.id] = wh.name; });
    return map;
  }, [warehouses]);

  const processedData = useMemo(() => {
    // Join Data
    let joined = rawInventory.map(inv => {
      const product = products.find(p => p.sku === inv.product?.sku) || {};
      const status = inv.available_qty < 0 ? 'Negative' : (inv.available_qty < (product.min_stock_level || 0) ? 'Low' : 'Healthy');
      return {
        ...inv,
        product_name: product.name || 'Unknown Product',
        brand: product.brand || '',
        min_stock_level: product.min_stock_level || 0,
        warehouse_name: warehouseMap[inv.warehouse_id] || `Warehouse ${inv.warehouse_id}`,
        status
      };
    });

    // Search
    if (search) {
      const lowerSearch = search.toLowerCase();
      joined = joined.filter(item => 
        (item.product?.sku?.toLowerCase() || '').includes(lowerSearch) ||
        (item.product_name?.toLowerCase() || '').includes(lowerSearch) ||
        (item.warehouse_name?.toLowerCase() || '').includes(lowerSearch)
      );
    }

    // Filter by Status (Low/Negative/Healthy)
    if (filterStatus) {
      joined = joined.filter(item => item.status === filterStatus);
    }

    // Pagination
    const startIndex = (page - 1) * limit;
    const paginated = joined.slice(startIndex, startIndex + limit);

    return {
      data: paginated,
      totalCount: joined.length,
      totalPages: Math.ceil(joined.length / limit)
    };
  }, [rawInventory, products, warehouseMap, search, filterStatus, page, limit]);

  return {
    isPending: invQuery.isPending || prodQuery.isPending || whQuery.isPending,
    error: invQuery.error || prodQuery.error || whQuery.error,
    refetch: () => { invQuery.refetch(); prodQuery.refetch(); whQuery.refetch(); },
    warehouses,
    ...processedData
  };
};

export const useUploadInventory = () => {
  const queryClient = useQueryClient();
  const companyId = useCompanyStore((state) => state.companyId);
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: async ({ warehouseCode, uploadType, file, preview, adminPassword }) => {
      const formData = new FormData();
      formData.append('warehouse_code', warehouseCode);
      formData.append('upload_type', uploadType);
      formData.append('file', file);
      if (preview) formData.append('preview', 'true');
      if (adminPassword) formData.append('admin_password', adminPassword);

      const response = await api.post('/api/inventory/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      if (!variables.preview) {
        queryClient.invalidateQueries({ queryKey: ['inventory'] });
        queryClient.invalidateQueries({ queryKey: ['warehouse'] });
        queryClient.invalidateQueries({ queryKey: ['inventoryHistory', companyId] });
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics', companyId] });
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'activity', companyId] });
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'alerts', companyId] });
        queryClient.invalidateQueries({ queryKey: ['reports'] });
        addNotification({ type: 'success', title: 'Upload Complete', message: data.message || 'Inventory uploaded successfully.' });
      }
    },
    onError: (err) => {
      handleApiError(err, 'An error occurred during upload.');
    }
  });
};

export const useManualAdjustment = () => {
  const companyId = useCompanyStore((state) => state.companyId);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore.getState();

  return useMutation({
    mutationFn: async ({ data, adminPassword }) => {
      const response = await api.post('/api/inventory/adjust', { ...data, admin_password: adminPassword });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse'] });
      queryClient.invalidateQueries({ queryKey: ['inventoryHistory', companyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics', companyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'activity', companyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'alerts', companyId] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      addNotification({ type: 'success', title: 'Adjustment Saved', message: 'Manual adjustment was processed successfully.' });
    },
    onError: (err) => {
      handleApiError(err, 'Failed to save manual adjustment.');
    }
  });
};

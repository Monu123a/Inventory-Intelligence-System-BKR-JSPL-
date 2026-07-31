import useCompanyStore from '../stores/useCompanyStore';
import { useQuery } from '@tanstack/react-query';
import * as inventoryService from '../services/inventory';
import * as productService from '../services/products';
import * as warehouseService from '../services/warehouses';
import { useMemo } from 'react';

const EMPTY_ARRAY = [];

export const useInventoryHistory = ({ search = '', dateRange = { start: '', end: '' }, warehouseId = '', sourceFilter = '', skuFilter = '', page = 1, limit = 20 }) => {
  const companyId = useCompanyStore((state) => state.companyId);
  const historyQuery = useQuery({
    queryKey: ['inventoryHistory', companyId],
    queryFn: inventoryService.getGlobalInventoryHistory,
  });

  const prodQuery = useQuery({
    queryKey: ['products', companyId],
    queryFn: productService.getProducts,
  });

  const whQuery = useQuery({
    queryKey: ['warehouses', companyId],
    queryFn: warehouseService.getWarehouses,
  });

  const rawHistory = historyQuery.data ?? EMPTY_ARRAY;
  const products = prodQuery.data ?? EMPTY_ARRAY;
  const warehouses = whQuery.data ?? EMPTY_ARRAY;

  // Build dynamic warehouse lookup
  const warehouseMap = useMemo(() => {
    const map = {};
    warehouses.forEach(wh => { map[wh.id] = wh.name; });
    return map;
  }, [warehouses]);

  const processedData = useMemo(() => {
    // 1. Join with products and warehouses
    let joined = rawHistory.map(record => {
      const product = products.find(p => p.sku === record.product_sku) || {};
      return {
        ...record,
        product_name: product.name || 'Unknown Product',
        warehouse_name: warehouseMap[record.warehouse_id] || `Warehouse ${record.warehouse_id}`,
      };
    });

    // 2. Filter by Date Range
    if (dateRange.start) {
      const start = new Date(dateRange.start).getTime();
      joined = joined.filter(r => new Date(r.timestamp).getTime() >= start);
    }
    if (dateRange.end) {
      const end = new Date(dateRange.end).getTime();
      joined = joined.filter(r => new Date(r.timestamp).getTime() <= end);
    }

    // 3. Filter by Warehouse
    if (warehouseId) {
      joined = joined.filter(r => String(r.warehouse_id) === String(warehouseId));
    }

    // 4. Filter by Source/Event Type
    if (sourceFilter) {
      joined = joined.filter(r => (r.source || '').toLowerCase() === sourceFilter.toLowerCase());
    }

    // 5. Filter by specific SKU
    if (skuFilter) {
      joined = joined.filter(r => (r.product_sku || '').toLowerCase() === skuFilter.toLowerCase());
    }

    // 6. Search across SKU, Product Name, Reference ID
    if (search) {
      const lowerSearch = search.toLowerCase();
      joined = joined.filter(r => 
        (r.product_sku || '').toLowerCase().includes(lowerSearch) ||
        (r.product_name || '').toLowerCase().includes(lowerSearch) ||
        (r.reference_id || '').toLowerCase().includes(lowerSearch)
      );
    }

    // Sort is inherently by timestamp desc from the backend, so we maintain it.

    // 7. Pagination
    const startIndex = (page - 1) * limit;
    const paginated = joined.slice(startIndex, startIndex + limit);

    return {
      allFilteredData: joined, // Kept for export
      data: paginated,
      totalCount: joined.length,
      totalPages: Math.ceil(joined.length / limit)
    };
  }, [rawHistory, products, warehouseMap, search, dateRange, warehouseId, sourceFilter, skuFilter, page, limit]);

  return {
    isPending: historyQuery.isPending || prodQuery.isPending || whQuery.isPending,
    error: historyQuery.error || prodQuery.error || whQuery.error,
    refetch: () => { historyQuery.refetch(); prodQuery.refetch(); whQuery.refetch(); },
    ...processedData
  };
};

export const useInventoryHistoryExport = () => {
  const exportToCsv = (filteredData) => {
    if (!filteredData || filteredData.length === 0) return;

    const headers = ['Timestamp', 'SKU', 'Product Name', 'Warehouse', 'Source', 'Qty Before', 'Qty Changed', 'Qty After', 'Reference ID'];
    const rows = filteredData.map(r => [
      new Date(r.timestamp).toLocaleString(),
      r.product_sku,
      r.product_name,
      r.warehouse_name,
      r.source,
      r.qty_before,
      r.qty_changed,
      r.qty_after,
      r.reference_id || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `inventory_history_${new Date().getTime()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return { exportToCsv };
};

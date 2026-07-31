import useCompanyStore from '../stores/useCompanyStore';
import { useQuery } from '@tanstack/react-query';
import * as inventoryService from '../services/inventory';
import * as productService from '../services/products';
import * as warehouseService from '../services/warehouses';
import { useMemo } from 'react';
import { 
  buildJoinedDataset, 
  buildLowStockReport, 
  buildNegativeStockReport, 
  buildWarehouseSummary, 
  buildInventoryValuation, 
  buildReplenishmentReport 
} from '../utils/reportTransformers';
import { saveDownloadMetadata } from './useDownloadHistory';

const EMPTY_ARRAY = [];

export const useReports = ({ reportType = 'LOW_STOCK', search = '', warehouseId = '', page = 1, limit = 15 }) => {
  const companyId = useCompanyStore((state) => state.companyId);
  const invQuery = useQuery({ queryKey: ['inventory', 'all', companyId], queryFn: () => inventoryService.getInventory(null) });
  const prodQuery = useQuery({ queryKey: ['products', companyId], queryFn: () => productService.getProducts(), enabled: !!companyId });
  const whQuery = useQuery({ queryKey: ['warehouses', companyId], queryFn: warehouseService.getWarehouses });

  const rawInventory = invQuery.data ?? EMPTY_ARRAY;
  const products = prodQuery.data ?? EMPTY_ARRAY;
  const warehouses = whQuery.data ?? EMPTY_ARRAY;

  const isPending = invQuery.isPending || prodQuery.isPending || whQuery.isPending;
  const error = invQuery.error || prodQuery.error || whQuery.error;
  
  // 1. Memoize Base Joined Data
  const joinedData = useMemo(() => {
    if (isPending) return [];
    return buildJoinedDataset(rawInventory, products, warehouses);
  }, [rawInventory, products, warehouses, isPending]);

  // 2. Memoize Report Generation (Includes Summary & Columns)
  const reportObj = useMemo(() => {
    if (!joinedData.length && !warehouses.length) return { data: [], summary: null, columns: [] };
    
    switch (reportType) {
      case 'NEGATIVE_STOCK': return buildNegativeStockReport(joinedData);
      case 'WAREHOUSE_SUMMARY': return buildWarehouseSummary(joinedData, warehouses);
      case 'INVENTORY_VALUATION': return buildInventoryValuation(joinedData);
      case 'DAILY_REPLENISHMENT': return buildReplenishmentReport(joinedData);
      case 'LOW_STOCK':
      default:
        return buildLowStockReport(joinedData);
    }
  }, [joinedData, warehouses, reportType]);

  // 3. Filter, Search, Sort, Paginate Data
  const processedData = useMemo(() => {
    let filtered = reportObj.data;

    // Filter by Warehouse (if applicable)
    if (warehouseId && reportType !== 'WAREHOUSE_SUMMARY') {
      filtered = filtered.filter(r => String(r.warehouse_id) === String(warehouseId));
    }

    // Global Search (SKU, Product, Warehouse)
    if (search) {
      const lowerSearch = search.toLowerCase();
      filtered = filtered.filter(r => 
        (r.product_sku || '').toLowerCase().includes(lowerSearch) ||
        (r.product_name || '').toLowerCase().includes(lowerSearch) ||
        (r.warehouse_name || '').toLowerCase().includes(lowerSearch)
      );
    }

    const totalCount = filtered.length;
    const startIndex = (page - 1) * limit;
    const paginated = filtered.slice(startIndex, startIndex + limit);

    return {
      allFilteredData: filtered,
      data: paginated,
      totalCount,
      totalPages: Math.ceil(totalCount / limit)
    };
  }, [reportObj.data, search, warehouseId, page, limit, reportType]);

  return {
    isPending,
    error,
    refetch: () => { invQuery.refetch(); prodQuery.refetch(); whQuery.refetch(); },
    summary: reportObj.summary,
    columns: reportObj.columns,
    warehouses,
    ...processedData
  };
};

export const useReportExport = () => {
  const companyCode = useCompanyStore((state) => state.companyCode);

  const exportToCsv = (filteredData, columns, reportType) => {
    if (!filteredData || filteredData.length === 0) return;

    // Extract headers from dynamic column definition
    const headers = columns.map(col => col.label);
    
    // Map rows based on column keys
    const rows = filteredData.map(row => 
      columns.map(col => {
        const val = row[col.key];
        return val !== undefined && val !== null ? val : '';
      })
    );

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    const safeName = reportType.toLowerCase().replace(/_/g, '-');
    const dateStr = new Date().toISOString().split('T')[0];
    const codePrefix = (companyCode || 'export').toLowerCase();
    const filename = `${codePrefix}_${safeName}_report_${dateStr}.csv`;
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Record Metadata
    saveDownloadMetadata({
      reportType,
      filename,
      rowCount: filteredData.length,
      filtersApplied: {}
    });
  };

  return { exportToCsv };
};

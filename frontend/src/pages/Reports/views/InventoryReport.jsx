import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { reportsService } from '../../../services/reports';
import { DataTable } from '../../../components/DataTable';
import { ReportToolbar } from '../../../components/Reporting/ReportToolbar';
import { FiFilter } from 'react-icons/fi';

export const InventoryReport = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  
  // New Filters
  const [company, setCompany] = useState('');
  const [stateHub, setStateHub] = useState('');
  const [warehouseType, setWarehouseType] = useState('');
  const [fcCode, setFcCode] = useState('');
  const [gstin, setGstin] = useState('');

  const limit = 20;

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['inventoryReport', { page, search, company, stateHub, warehouseType, fcCode, gstin }],
    queryFn: async () => {
      const params = { skip: (page - 1) * limit, limit };
      if (search) params.search = search;
      if (company) params.company = company;
      if (stateHub) params.state_hub = stateHub;
      if (warehouseType) params.warehouse_type = warehouseType;
      if (fcCode) params.fc_code = fcCode;
      if (gstin) params.gstin = gstin;
      
      return reportsService.getInventoryReport(params);
    }
  });

  const items = data?.items || (Array.isArray(data) ? data : []);
  const total = data?.total || items.length;
  const totalPages = Math.ceil(total / limit);

  const columns = [
    { key: 'sku', label: 'SKU' },
    { key: 'product_name', label: 'Product' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'current_qty', label: 'On Hand' },
    { key: 'reserved_qty', label: 'Reserved' },
    { key: 'available_qty', label: 'Available' }
  ];

  return (
    <div>
      <ReportToolbar 
        searchPlaceholder="Search products or SKU..."
        searchValue={search}
        onSearchChange={(val) => { setSearch(val); setPage(1); }}
        showDateRange={false}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
        exportEndpoint="/api/business-reports/inventory/export"
        exportFileName="inventory_report.csv"
        onPrint={() => window.print()}
      />
      
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '16px', padding: '16px 24px', 
        backgroundColor: '#fff', borderBottom: '1px solid #e5e7eb', alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: '#4b5563', fontSize: '14px' }}>
          <FiFilter /> Filters:
        </div>
        
        <select 
          style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', outline: 'none', fontSize: '14px', backgroundColor: '#f9fafb' }}
          value={company} onChange={(e) => { setCompany(e.target.value); setPage(1); }}
        >
          <option value="">All Companies</option>
          <option value="BKR">BKR</option>
          <option value="JSPL">JSPL</option>
        </select>

        <select 
          style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', outline: 'none', fontSize: '14px', backgroundColor: '#f9fafb' }}
          value={stateHub} onChange={(e) => { setStateHub(e.target.value); setPage(1); }}
        >
          <option value="">All State Hubs</option>
          <option value="MH">Maharashtra (MH)</option>
          <option value="KA">Karnataka (KA)</option>
          <option value="DL">Delhi (DL)</option>
          <option value="UP">Uttar Pradesh (UP)</option>
        </select>

        <select 
          style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', outline: 'none', fontSize: '14px', backgroundColor: '#f9fafb' }}
          value={warehouseType} onChange={(e) => { setWarehouseType(e.target.value); setPage(1); }}
        >
          <option value="">All Warehouse Types</option>
          <option value="Fulfillment Center">Fulfillment Center</option>
          <option value="Regional Hub">Regional Hub</option>
          <option value="Store">Store</option>
        </select>

        <input 
          type="text" 
          placeholder="FC Code" 
          style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', outline: 'none', fontSize: '14px', width: '120px' }}
          value={fcCode} onChange={(e) => { setFcCode(e.target.value); setPage(1); }}
        />

        <input 
          type="text" 
          placeholder="GSTIN" 
          style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', outline: 'none', fontSize: '14px', width: '150px' }}
          value={gstin} onChange={(e) => { setGstin(e.target.value); setPage(1); }}
        />
      </div>

      <DataTable 
        columns={columns}
        data={items}
        isLoading={isLoading}
        isError={isError}
        errorMessage={error?.message || "Failed to load inventory report"}
        hasActiveFilters={!!search || !!company || !!stateHub || !!warehouseType || !!fcCode || !!gstin}
        pagination={{
          currentPage: page,
          totalPages: totalPages || 1,
          onPageChange: setPage
        }}
        onRowClick={(row) => {
          if (row.sku) navigate(`/inventory-history?sku=${row.sku}`);
        }}
      />
    </div>
  );
};

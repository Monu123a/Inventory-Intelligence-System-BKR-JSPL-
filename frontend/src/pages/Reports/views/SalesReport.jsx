import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { DataTable } from '../../../components/DataTable';
import { ReportToolbar } from '../../../components/Reporting/ReportToolbar';

export const SalesReport = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const limit = 20;

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['salesReport', { page, search, dateFrom, dateTo }],
    queryFn: async () => {
      const params = { skip: (page - 1) * limit, limit };
      if (search) params.search = search;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      const res = await api.get('/api/business-reports/sales', { params });
      return res.data; // Expected format: { items: [], total: number } or similar array
    }
  });

  // Handle backend formats flexibly
  const items = data?.items || (Array.isArray(data) ? data : []);
  const total = data?.total || items.length;
  const totalPages = Math.ceil(total / limit);

  const columns = [
    { key: 'sale_date', label: 'Date', render: (val) => new Date(val).toLocaleDateString() },
    { key: 'bill_number', label: 'Bill No.' },
    { key: 'customer_name', label: 'Customer' },
    { key: 'total_quantity', label: 'Qty' },
    { key: 'grand_total', label: 'Total Value', render: (val) => `₹${Number(val || 0).toFixed(2)}` },
    { key: 'status', label: 'Status' }
  ];

  return (
    <div>
      <ReportToolbar 
        searchPlaceholder="Search invoices..."
        searchValue={search}
        onSearchChange={(val) => { setSearch(val); setPage(1); }}
        startDate={dateFrom}
        endDate={dateTo}
        onStartDateChange={(val) => { setDateFrom(val); setPage(1); }}
        onEndDateChange={(val) => { setDateTo(val); setPage(1); }}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
        exportEndpoint="/api/business-reports/sales/export"
        exportFileName="sales_report.csv"
        onPrint={() => window.print()}
      />
      <DataTable 
        columns={columns}
        data={items}
        isLoading={isLoading}
        isError={isError}
        errorMessage={error?.message || "Failed to load sales report"}
        hasActiveFilters={!!(search || dateFrom || dateTo)}
        pagination={{
          currentPage: page,
          totalPages: totalPages || 1,
          onPageChange: setPage
        }}
        onRowClick={(row) => {
          if (row.id) navigate(`/sales/${row.id}/invoice`);
        }}
      />
    </div>
  );
};

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { DataTable } from '../../../components/DataTable';
import { ReportToolbar } from '../../../components/Reporting/ReportToolbar';

export const DefectiveReport = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const limit = 20;

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['defectiveReport', { page, search, dateFrom, dateTo }],
    queryFn: async () => {
      const params = { skip: (page - 1) * limit, limit };
      if (search) params.search = search;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      const res = await api.get('/api/business-reports/defective', { params });
      return res.data;
    }
  });

  const items = data?.items || (Array.isArray(data) ? data : []);
  const total = data?.total || items.length;
  const totalPages = Math.ceil(total / limit);

  const columns = [
    { key: 'logged_date', label: 'Date', render: (val) => new Date(val).toLocaleDateString() },
    { key: 'sku', label: 'SKU' },
    { key: 'product_name', label: 'Product Name' },
    { key: 'quantity', label: 'Quantity' },
    { key: 'defect_reason', label: 'Defect Reason' },
    { key: 'source', label: 'Source' },
    { key: 'status', label: 'Status' }
  ];

  return (
    <div>
      <ReportToolbar 
        searchPlaceholder="Search defective stock..."
        searchValue={search}
        onSearchChange={(val) => { setSearch(val); setPage(1); }}
        startDate={dateFrom}
        endDate={dateTo}
        onStartDateChange={(val) => { setDateFrom(val); setPage(1); }}
        onEndDateChange={(val) => { setDateTo(val); setPage(1); }}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
        exportEndpoint="/api/business-reports/defective/export"
        exportFileName="defective_report.csv"
        onPrint={() => window.print()}
      />
      <DataTable 
        columns={columns}
        data={items}
        isLoading={isLoading}
        isError={isError}
        errorMessage={error?.message || "Failed to load defective report"}
        hasActiveFilters={!!(search || dateFrom || dateTo)}
        pagination={{
          currentPage: page,
          totalPages: totalPages || 1,
          onPageChange: setPage
        }}
        onRowClick={(row) => {
          if (row.id) navigate(`/inventory/defective?search=${row.sku || ''}`);
        }}
      />
    </div>
  );
};

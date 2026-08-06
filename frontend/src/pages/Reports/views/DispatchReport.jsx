import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { DataTable } from '../../../components/DataTable';
import { ReportToolbar } from '../../../components/Reporting/ReportToolbar';

export const DispatchReport = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const limit = 20;

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['dispatchReport', { page, search, dateFrom, dateTo }],
    queryFn: async () => {
      const params = { skip: (page - 1) * limit, limit };
      if (search) params.search = search;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      const res = await api.get('/api/business-reports/dispatches', { params });
      return res.data;
    }
  });

  const items = data?.items || (Array.isArray(data) ? data : []);
  const total = data?.total || items.length;
  const totalPages = Math.ceil(total / limit);

  const columns = [
    { key: 'dispatch_date', label: 'Date', render: (val) => new Date(val).toLocaleDateString() },
    { key: 'dispatch_number', label: 'Dispatch No.' },
    { key: 'warehouse_name', label: 'Origin Warehouse' },
    { key: 'destination', label: 'Destination' },
    { key: 'status', label: 'Status' },
    { key: 'total_items', label: 'Total Items' }
  ];

  return (
    <div>
      <ReportToolbar 
        searchPlaceholder="Search dispatches..."
        searchValue={search}
        onSearchChange={(val) => { setSearch(val); setPage(1); }}
        startDate={dateFrom}
        endDate={dateTo}
        onStartDateChange={(val) => { setDateFrom(val); setPage(1); }}
        onEndDateChange={(val) => { setDateTo(val); setPage(1); }}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
        exportEndpoint="/api/business-reports/dispatches/export"
        exportFileName="dispatch_report.csv"
        onPrint={() => window.print()}
      />
      <DataTable 
        columns={columns}
        data={items}
        isLoading={isLoading}
        isError={isError}
        errorMessage={error?.message || "Failed to load dispatch report"}
        hasActiveFilters={!!(search || dateFrom || dateTo)}
        pagination={{
          currentPage: page,
          totalPages: totalPages || 1,
          onPageChange: setPage
        }}
        onRowClick={(row) => {
          if (row.id) navigate(`/logistics/dispatches/${row.id}`);
        }}
      />
    </div>
  );
};

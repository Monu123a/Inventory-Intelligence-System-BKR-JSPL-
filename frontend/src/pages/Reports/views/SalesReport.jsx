import React, { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import useCompanyStore from '../../../stores/useCompanyStore';
import { reportsService } from '../../../services/reports';
import { saveDownloadMetadata } from '../../../hooks/useDownloadHistory';
import { DataTable } from '../../../components/DataTable';
import { ReportToolbar } from '../../../components/Reporting/ReportToolbar';
import { FiDownload, FiFileText } from 'react-icons/fi';

export const SalesReport = () => {
  const navigate = useNavigate();
  const { currentCompany, companyId } = useCompanyStore();
  const companyCode = (currentCompany?.code || '').toUpperCase();
  const isBkr = companyCode === 'BKR' || companyId === 2;
  const isJspl = companyCode === 'JSPL' || companyId === 3;

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedSeries, setSelectedSeries] = useState('GST');
  const [isExporting, setIsExporting] = useState(false);
  const limit = 20;

  const seriesOptions = useMemo(() => {
    if (isJspl) {
      return [
        { value: 'GST', label: 'GST Series (GST-)' },
        { value: 'JGST', label: 'JSPL Series (JGST-)' },
        { value: 'AFN', label: 'Amazon AFN (FBA Orders)' },
        { value: 'MFN', label: 'Amazon MFN (Merchant Orders)' },
        { value: 'AMAZON', label: 'Amazon All (AFN & MFN)' },
        { value: 'SERVICE', label: 'Service Series (SERVICE-)' },
        { value: 'ALL', label: 'All Series (Excl. Amazon)' }
      ];
    }
    if (isBkr) {
      return [
        { value: 'GST', label: 'GST Series (GST- / BKR-GST-)' },
        { value: 'BKR', label: 'BKR Series (BKR-)' },
        { value: 'AFN', label: 'Amazon AFN (FBA Orders)' },
        { value: 'MFN', label: 'Amazon MFN (Merchant Orders)' },
        { value: 'AMAZON', label: 'Amazon All (AFN & MFN)' },
        { value: 'ALL', label: 'All Series (Excl. Amazon)' }
      ];
    }
    return [
      { value: 'GST', label: 'GST Series (GST-)' },
      { value: 'AFN', label: 'Amazon AFN (FBA Orders)' },
      { value: 'MFN', label: 'Amazon MFN (Merchant Orders)' },
      { value: 'AMAZON', label: 'Amazon All (AFN & MFN)' },
      { value: 'ALL', label: 'All Series (Excl. Amazon)' }
    ];
  }, [isJspl, isBkr]);

  useEffect(() => {
    if (isJspl && selectedSeries === 'BKR') {
      setSelectedSeries('GST');
    } else if (isBkr && (selectedSeries === 'JGST' || selectedSeries === 'SERVICE')) {
      setSelectedSeries('GST');
    }
  }, [isJspl, isBkr, selectedSeries]);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['salesReport', { page, search, dateFrom, dateTo, selectedSeries, companyId }],
    queryFn: async () => {
      const params = { page, limit };
      if (search?.trim()) params.search = search.trim();
      if (dateFrom?.trim()) params.date_from = dateFrom.trim();
      if (dateTo?.trim()) params.date_to = dateTo.trim();
      if (selectedSeries) params.series = selectedSeries;
      
      return reportsService.getSalesReport(params);
    }
  });

  const handleExportAccountantReport = async (format) => {
    setIsExporting(true);
    try {
      const response = await reportsService.downloadSeriesReport({
        series: selectedSeries,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        format
      });

      const contentDisposition = response.headers['content-disposition'] || '';
      let filename = `Accountant_Sales_${selectedSeries}_${format === 'excel' ? 'xlsx' : 'csv'}`;
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }

      const blob = new Blob([response.data], {
        type: format === 'excel'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'text/csv;charset=utf-8;'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);

      saveDownloadMetadata({
        reportType: `ACCOUNTANT_SALES_${selectedSeries}`,
        filename,
        rowCount: response.headers['x-row-count'] ? parseInt(response.headers['x-row-count']) : undefined,
        fileFormat: format.toUpperCase(),
        status: 'Completed'
      });
    } catch (err) {
      console.error('Accountant report export failed:', err);
      let errorMsg = err.message;
      if (err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const parsed = JSON.parse(text);
          errorMsg = parsed.detail || parsed.message || text;
        } catch {
          // ignore
        }
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      }
      alert('Failed to export report: ' + errorMsg);
    } finally {
      setIsExporting(false);
    }
  };

  // Handle backend formats flexibly
  const items = data?.items || data?.data || (Array.isArray(data) ? data : []);
  const total = data?.total_records ?? data?.total ?? items.length;
  const totalPages = data?.total_pages || Math.ceil(total / limit) || 1;

  const columns = [
    { key: 'period', label: 'Period' },
    { key: 'total_orders', label: 'Total Orders' },
    { key: 'total_items_sold', label: 'Total Items Sold' },
    { key: 'total_revenue', label: 'Total Revenue', render: (val) => `₹${Number(val || 0).toFixed(2)}` }
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
        customFilters={[
          {
            label: 'Series',
            value: selectedSeries,
            onChange: setSelectedSeries,
            options: seriesOptions
          }
        ]}
        onRefresh={() => refetch()}
        isRefreshing={isFetching}
        exportEndpoint="/api/reports/series-wise/export"
        exportParams={{ series: selectedSeries, format: 'csv' }}
        exportFileName={`Accountant_Sales_${selectedSeries}.csv`}
        onPrint={() => window.print()}
      />

      {/* Series Accountant Report Download Banner */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', margin: '12px 16px', padding: '10px 14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FiFileText style={{ color: '#2563eb', fontSize: '18px' }} />
          <div>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
              Accountant 47-Column Report ({selectedSeries} Series)
            </span>
            <span style={{ display: 'block', fontSize: '11px', color: '#64748b' }}>
              Matches government return & accounting format with itemized taxes and bill subtotals.
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={() => handleExportAccountantReport('csv')}
            disabled={isExporting}
            style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '6px 14px', background: '#059669', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', opacity: isExporting ? 0.7 : 1 }}
          >
            <FiDownload /> {isExporting ? 'Exporting...' : 'Download CSV'}
          </button>
          <button
            type="button"
            onClick={() => handleExportAccountantReport('excel')}
            disabled={isExporting}
            style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '6px 14px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', opacity: isExporting ? 0.7 : 1 }}
          >
            <FiFileText /> {isExporting ? 'Exporting...' : 'Download Excel (.xlsx)'}
          </button>
        </div>
      </div>

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

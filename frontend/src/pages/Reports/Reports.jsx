import React, { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import { SearchBar } from '../../components/forms/SearchBar';
import Button from '../../components/forms/Button';
import { ReportSelector } from './components/ReportSelector';
import { ReportSummaryCard } from './components/ReportSummaryCard';
import { useReports, useReportExport } from '../../hooks/useReports';
import { FiDownload, FiRefreshCw } from 'react-icons/fi';
import styles from './Reports.module.css';

const Reports = () => {
  const [reportType, setReportType] = useState('LOW_STOCK');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [warehouseId, setWarehouseId] = useState('');

  const { data, allFilteredData, columns, summary, totalPages, isPending, refetch, warehouses } = useReports({
    reportType, search, warehouseId, page, limit: 15
  });

  const { exportToCsv } = useReportExport();

  const handleReportChange = (newType) => {
    setReportType(newType);
    setPage(1);
    setSearch('');
    setWarehouseId('');
  };

  const handleSearch = (val) => { setSearch(val); setPage(1); };

  const handleExport = () => {
    exportToCsv(allFilteredData, columns, reportType);
  };

  return (
    <PageContainer 
      title="Operational Reports"
      actions={
        <>
          <Button variant="secondary" onClick={() => refetch()} isLoading={isPending}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh Data
          </Button>
          <Button variant="primary" onClick={handleExport} disabled={!allFilteredData || allFilteredData.length === 0 || isPending}>
            <FiDownload style={{ marginRight: '8px' }} /> Export to CSV
          </Button>
        </>
      }
    >
      <Card noPadding>
        <ReportSelector activeReport={reportType} onSelect={handleReportChange} />
        
        <ReportSummaryCard summary={summary} />

        <div className={styles.toolbar}>
          <SearchBar 
            onSearch={handleSearch} 
            placeholder="Search report..." 
            value={search}
          />
          {reportType !== 'WAREHOUSE_SUMMARY' && (
            <select 
              className={styles.filter} 
              value={warehouseId} 
              onChange={e => { setWarehouseId(e.target.value); setPage(1); }}
            >
              <option value="">All Warehouses</option>
              {(warehouses || []).map(wh => <option key={wh.id} value={wh.id}>{wh.name}</option>)}
            </select>
          )}
        </div>

        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {isPending ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Generating Report...</td></tr>
              ) : data?.length === 0 ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>This report contains no data.</td></tr>
              ) : (
                data?.map((row, idx) => (
                  <TableRow key={row.id || row.product_sku || row.warehouse_name || idx} row={row} columns={columns} />
                ))
              )}
            </tbody>
          </DataTable>

          {totalPages > 1 && (
            <TablePagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
          )}
        </div>
      </Card>
    </PageContainer>
  );
};

export default Reports;

import React, { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import { StatusBadge } from '../../components/StatusBadge/StatusBadge';
import { SearchBar } from '../../components/forms/SearchBar';
import Button from '../../components/forms/Button';
import { ConfirmationDialog } from '../../components/Modal/ConfirmationDialog';
import { DownloadHistoryModal } from './components/DownloadHistoryModal';
import { useDownloadHistory } from '../../hooks/useDownloadHistory';
import { FiRefreshCw, FiTrash2, FiEye } from 'react-icons/fi';
import styles from './DownloadCentre.module.css';

const REPORTS = [
  { id: 'LOW_STOCK', label: 'Low Stock' },
  { id: 'NEGATIVE_STOCK', label: 'Negative Stock' },
  { id: 'DAILY_REPLENISHMENT', label: 'Daily Replenishment' },
  { id: 'WAREHOUSE_SUMMARY', label: 'Warehouse Summary' },
  { id: 'INVENTORY_VALUATION', label: 'Inventory Valuation' }
];

const DownloadCentre = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [reportTypeFilter, setReportTypeFilter] = useState('');
  
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);

  const { 
    data, 
    totalPages, 
    isError, 
    loadHistory, 
    clearHistory, 
    removeHistoryItem,
    resetCorruptedHistory
  } = useDownloadHistory({ search, reportTypeFilter, page, limit: 15 });

  const handleSearch = (val) => { setSearch(val); setPage(1); };

  const columns = [
    { key: 'reportType', label: 'Report Type', render: (val) => <span className={styles.typeText}>{val.replace(/_/g, ' ')}</span> },
    { key: 'filename', label: 'Filename', render: (val) => <span className={styles.filename}>{val}</span> },
    { key: 'generatedAt', label: 'Generated At', render: (val) => new Date(val).toLocaleString() },
    { key: 'rowCount', label: 'Rows', render: (val) => val },
    { key: 'fileFormat', label: 'Format', render: (val) => val },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div className={styles.actionsGroup}>
          <button className={styles.iconBtn} title="View Metadata" onClick={() => setSelectedRecord(row)}><FiEye /></button>
          <button className={`${styles.iconBtn} ${styles.dangerBtn}`} title="Remove from History" onClick={() => removeHistoryItem(row.id)}><FiTrash2 /></button>
        </div>
      )
    }
  ];

  if (isError) {
    return (
      <PageContainer title="Download Centre">
        <Card>
          <div className={styles.errorState}>
            <h3>Storage Error</h3>
            <p>Your download history appears to be corrupted and cannot be loaded.</p>
            <Button variant="primary" onClick={resetCorruptedHistory}>Reset History</Button>
          </div>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer 
      title="Download Centre"
      actions={
        <>
          <Button variant="secondary" onClick={loadHistory}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
          </Button>
          <Button variant="secondary" onClick={() => setIsConfirmClearOpen(true)} disabled={data.length === 0}>
            <FiTrash2 style={{ marginRight: '8px' }} /> Clear History
          </Button>
        </>
      }
    >
      <Card noPadding>
        <div className={styles.toolbar}>
          <SearchBar onSearch={handleSearch} placeholder="Search by filename..." />
          <select 
            className={styles.filter} 
            value={reportTypeFilter} 
            onChange={e => { setReportTypeFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Report Types</option>
            {REPORTS.map(r => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </div>

        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {data?.length === 0 ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No download history available.</td></tr>
              ) : (
                data?.map((row) => (
                  <TableRow key={row.id} row={row} columns={columns} />
                ))
              )}
            </tbody>
          </DataTable>

          {totalPages > 1 && (
            <TablePagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
          )}
        </div>
      </Card>

      <DownloadHistoryModal 
        isOpen={!!selectedRecord} 
        onClose={() => setSelectedRecord(null)} 
        record={selectedRecord}
      />

      <ConfirmationDialog 
        isOpen={isConfirmClearOpen}
        onClose={() => setIsConfirmClearOpen(false)}
        onConfirm={() => {
          clearHistory();
          setIsConfirmClearOpen(false);
        }}
        title="Clear Download History"
        message="Are you sure you want to clear your entire download history? This action cannot be undone."
        confirmText="Clear History"
        isDanger={true}
      />
    </PageContainer>
  );
};

export default DownloadCentre;

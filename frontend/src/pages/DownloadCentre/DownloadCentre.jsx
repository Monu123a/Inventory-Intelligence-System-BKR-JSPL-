import React, { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import { StatusBadge } from '../../components/StatusBadge/StatusBadge';
import { SearchBar } from '../../components/forms/SearchBar';
import Button from '../../components/forms/Button';
import { ConfirmationDialog } from '../../components/Modal/ConfirmationDialog';
import { DownloadHistoryModal } from './components/DownloadHistoryModal';
import { useDownloadHistory, saveDownloadMetadata } from '../../hooks/useDownloadHistory';
import { reportsService } from '../../services/reports';
import { FiRefreshCw, FiTrash2, FiEye, FiDownload, FiFileText, FiCalendar, FiCheck } from 'react-icons/fi';
import styles from './DownloadCentre.module.css';

const REPORTS = [
  { id: 'ACCOUNTANT_SALES', label: 'Accountant Sales (Series-Wise)' },
  { id: 'LOW_STOCK', label: 'Low Stock' },
  { id: 'NEGATIVE_STOCK', label: 'Negative Stock' },
  { id: 'DAILY_REPLENISHMENT', label: 'Daily Replenishment' },
  { id: 'WAREHOUSE_SUMMARY', label: 'Warehouse Summary' },
  { id: 'INVENTORY_VALUATION', label: 'Inventory Valuation' }
];

const SERIES_PRESETS = [
  { id: 'GST', label: 'GST Series (GST- / BKR-GST- / JGST-)' },
  { id: 'AMAZON', label: 'Amazon Series (SP-API & AFN/MFN)' },
  { id: 'BKR', label: 'BKR Retail Series (BKR-)' },
  { id: 'JGST', label: 'JSPL GST Series (JGST-)' },
  { id: 'ALL', label: 'All Series (Combined)' },
  { id: 'CUSTOM', label: 'Custom Series...' }
];

const DownloadCentre = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [reportTypeFilter, setReportTypeFilter] = useState('');
  
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);

  // Series Report Generator State
  const [selectedSeries, setSelectedSeries] = useState('GST');
  const [customSeries, setCustomSeries] = useState('');
  const [dateFrom, setDateFrom] = useState('2026-10-01');
  const [dateTo, setDateTo] = useState('2027-03-31');
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState(null);

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

  const handleDownloadSeriesReport = async (format) => {
    const finalSeries = selectedSeries === 'CUSTOM' ? (customSeries.trim() || 'GST') : selectedSeries;
    setIsExporting(true);
    setExportFormat(format);
    try {
      const response = await reportsService.downloadSeriesReport({
        series: finalSeries,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        format
      });

      const contentDisposition = response.headers['content-disposition'] || '';
      let filename = `Accountant_Sales_${finalSeries}_${format === 'excel' ? 'xlsx' : 'csv'}`;
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
        reportType: `ACCOUNTANT_SALES_${finalSeries}`,
        filename,
        rowCount: response.headers['x-row-count'] ? parseInt(response.headers['x-row-count']) : undefined,
        fileFormat: format.toUpperCase(),
        status: 'Completed'
      });

      loadHistory();
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to generate report: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsExporting(false);
      setExportFormat(null);
    }
  };

  const setPresetRange = (preset) => {
    if (preset === 'FY26') {
      setDateFrom('2026-10-01');
      setDateTo('2027-03-31');
    } else if (preset === 'THIS_MONTH') {
      setDateFrom('2026-10-01');
      setDateTo('2026-10-31');
    } else if (preset === 'ALL_TIME') {
      setDateFrom('');
      setDateTo('');
    }
  };

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
      {/* Series-Wise Sales Report Generator Card */}
      <Card noPadding style={{ marginBottom: '24px', overflow: 'visible' }}>
        <div className={styles.seriesSection}>
          <div className={styles.seriesHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: '#dbeafe', color: '#1d4ed8', padding: '8px', borderRadius: '8px', display: 'flex' }}>
                <FiFileText size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#0f172a' }}>
                  Series-Wise Sales Reports (Accountant 47-Column Format)
                </h3>
                <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: '#64748b' }}>
                  Download official tax-formatted reports for GST series, Amazon series, and retail series with automatic bill subtotals.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                type="button"
                className={styles.btnDownloadCsv}
                onClick={() => handleDownloadSeriesReport('csv')}
                disabled={isExporting}
                title="Download in standard 47-column CSV format"
              >
                <FiDownload className={isExporting && exportFormat === 'csv' ? styles.spin : ''} />
                {isExporting && exportFormat === 'csv' ? 'Generating CSV...' : 'Download CSV'}
              </button>
              <button 
                type="button"
                className={styles.btnDownloadExcel}
                onClick={() => handleDownloadSeriesReport('excel')}
                disabled={isExporting}
                title="Download styled Microsoft Excel workbook with formulas"
              >
                <FiFileText className={isExporting && exportFormat === 'excel' ? styles.spin : ''} />
                {isExporting && exportFormat === 'excel' ? 'Generating Excel...' : 'Download Excel (.xlsx)'}
              </button>
            </div>
          </div>

          {/* Series Pills */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Select Invoice / Order Series
            </div>
            <div className={styles.seriesPills}>
              {SERIES_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={`${styles.pillBtn} ${selectedSeries === preset.id ? styles.pillBtnActive : ''}`}
                  onClick={() => setSelectedSeries(preset.id)}
                >
                  {selectedSeries === preset.id && <FiCheck style={{ marginRight: '4px', verticalAlign: 'middle' }} />}
                  {preset.label}
                </button>
              ))}
              {selectedSeries === 'CUSTOM' && (
                <input
                  type="text"
                  className={styles.customInput}
                  placeholder="Enter prefix (e.g. GST-)"
                  value={customSeries}
                  onChange={(e) => setCustomSeries(e.target.value)}
                  autoFocus
                />
              )}
            </div>
          </div>

          {/* Controls: Date Range & Presets */}
          <div className={styles.controlsRow}>
            <div className={styles.filterGroup}>
              <span className={styles.label}>Date Range:</span>
              <input 
                type="date"
                className={styles.dateInput}
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                title="From Date"
              />
              <span style={{ color: '#94a3b8', fontSize: '13px' }}>to</span>
              <input 
                type="date"
                className={styles.dateInput}
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                title="To Date"
              />
            </div>

            <div className={styles.filterGroup}>
              <span className={styles.label}>Quick Presets:</span>
              <button 
                type="button"
                className={styles.pillBtn} 
                style={{ fontSize: '11px', padding: '2px 8px' }}
                onClick={() => setPresetRange('FY26')}
              >
                FY 2026-27 (01/10/26 – 31/03/27)
              </button>
              <button 
                type="button"
                className={styles.pillBtn} 
                style={{ fontSize: '11px', padding: '2px 8px' }}
                onClick={() => setPresetRange('THIS_MONTH')}
              >
                October 2026
              </button>
              <button 
                type="button"
                className={styles.pillBtn} 
                style={{ fontSize: '11px', padding: '2px 8px' }}
                onClick={() => setPresetRange('ALL_TIME')}
              >
                All Time
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Download History Card */}
      <Card noPadding>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0' }}>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#1e293b' }}>
            Generated Reports & Download History
          </h3>
        </div>
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

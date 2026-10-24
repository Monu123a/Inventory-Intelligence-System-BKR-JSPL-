import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TablePagination } from '../../components/DataTable';
import { StatusBadge } from '../../components/StatusBadge/StatusBadge';
import { SearchBar } from '../../components/forms/SearchBar';
import Button from '../../components/forms/Button';
import { ConfirmationDialog } from '../../components/Modal/ConfirmationDialog';
import { DownloadHistoryModal } from './components/DownloadHistoryModal';
import { useDownloadHistory, saveDownloadMetadata } from '../../hooks/useDownloadHistory';
import useCompanyStore from '../../stores/useCompanyStore';
import { reportsService } from '../../services/reports';
import api from '../../services/api';
import { 
  FiRefreshCw, FiTrash2, FiEye, FiDownload, FiFileText, 
  FiCheck, FiShoppingBag, FiTruck, FiRotateCcw, FiLayers
} from 'react-icons/fi';
import styles from './DownloadCentre.module.css';

const REPORTS = [
  { id: 'ACCOUNTANT_SALES', label: 'Accountant Sales (Series-Wise)' },
  { id: 'ACCOUNTANT_PURCHASES', label: 'Accountant Purchase Register' },
  { id: 'ACCOUNTANT_AMAZON_RETURNS', label: 'Accountant Amazon Returns' },
  { id: 'ACCOUNTANT_SALES_RETURNS', label: 'Accountant POS Returns' },
  { id: 'LOW_STOCK', label: 'Low Stock' },
  { id: 'NEGATIVE_STOCK', label: 'Negative Stock' },
  { id: 'DAILY_REPLENISHMENT', label: 'Daily Replenishment' },
  { id: 'WAREHOUSE_SUMMARY', label: 'Warehouse Summary' },
  { id: 'INVENTORY_VALUATION', label: 'Inventory Valuation' }
];

const REPORT_CATEGORIES = [
  { 
    id: 'sales', 
    label: 'Sales (Series-Wise)', 
    icon: FiFileText,
    title: 'Series-Wise Sales Reports (Accountant 47-Column Format)',
    desc: 'Official tax-formatted sales reports for GST series, Amazon series, and retail series with automatic bill subtotals and grand totals.'
  },
  { 
    id: 'purchases', 
    label: 'Purchase Register', 
    icon: FiShoppingBag,
    title: 'Vendor Purchase Register (Accountant 47-Column Format)',
    desc: 'Comprehensive vendor purchase register with bill-wise GST split (CGST/SGST/IGST), unit costs, payment status, and bill subtotals.'
  },
  { 
    id: 'amazon_returns', 
    label: 'Amazon Returns', 
    icon: FiTruck,
    title: 'Amazon Customer Returns Register (Accountant 47-Column Format)',
    desc: 'Amazon SP-API return shipments, FC inspection reports, and reverse logistics in official accountant 47-column format.'
  },
  { 
    id: 'sales_returns', 
    label: 'POS Sales Returns', 
    icon: FiRotateCcw,
    title: 'Offline POS Returns & Credit Notes (Accountant 47-Column Format)',
    desc: 'Retail counter sales returns, customer credit notes, and tax reversals formatted for your accountant.'
  }
];

const DownloadCentre = () => {
  const { currentCompany, companyId } = useCompanyStore();
  const companyCode = (currentCompany?.code || '').toUpperCase();
  const isBkr = companyCode === 'BKR' || companyId === 2;
  const isJspl = companyCode === 'JSPL' || companyId === 3;

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [reportTypeFilter, setReportTypeFilter] = useState('');
  
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);

  // Active Category State
  const [selectedCategory, setSelectedCategory] = useState('sales');

  // Series Report Generator State
  const [selectedSeries, setSelectedSeries] = useState('GST');
  const [customSeries, setCustomSeries] = useState('');
  const [dateFrom, setDateFrom] = useState('2026-10-01');
  const [dateTo, setDateTo] = useState('2027-03-31');
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState(null);

  const seriesPresets = React.useMemo(() => {
    if (isJspl) {
      return [
        { id: 'GST', label: 'GST Series (GST-)' },
        { id: 'JGST', label: 'JSPL GST Series (JGST-)' },
        { id: 'AFN', label: 'Amazon AFN (FBA Orders)' },
        { id: 'MFN', label: 'Amazon MFN (Merchant Orders)' },
        { id: 'AMAZON', label: 'Amazon All (AFN & MFN)' },
        { id: 'SERVICE', label: 'Service Series (SERVICE-)' },
        { id: 'ALL', label: 'All Series (Excl. Amazon)' },
        { id: 'CUSTOM', label: 'Custom Series...' }
      ];
    }
    if (isBkr) {
      return [
        { id: 'GST', label: 'GST Series (GST- / BKR-GST-)' },
        { id: 'BKR', label: 'BKR Retail Series (BKR-)' },
        { id: 'AFN', label: 'Amazon AFN (FBA Orders)' },
        { id: 'MFN', label: 'Amazon MFN (Merchant Orders)' },
        { id: 'AMAZON', label: 'Amazon All (AFN & MFN)' },
        { id: 'ALL', label: 'All Series (Excl. Amazon)' },
        { id: 'CUSTOM', label: 'Custom Series...' }
      ];
    }
    return [
      { id: 'GST', label: 'GST Series (GST-)' },
      { id: 'AFN', label: 'Amazon AFN (FBA Orders)' },
      { id: 'MFN', label: 'Amazon MFN (Merchant Orders)' },
      { id: 'AMAZON', label: 'Amazon All (AFN & MFN)' },
      { id: 'ALL', label: 'All Series (Excl. Amazon)' },
      { id: 'CUSTOM', label: 'Custom Series...' }
    ];
  }, [isJspl, isBkr]);

  useEffect(() => {
    if (isJspl && selectedSeries === 'BKR') {
      setSelectedSeries('GST');
    } else if (isBkr && (selectedSeries === 'JGST' || selectedSeries === 'SERVICE')) {
      setSelectedSeries('GST');
    }
  }, [isJspl, isBkr, selectedSeries]);

  // Vendor list for Purchases category
  const [vendors, setVendors] = useState([]);
  const [selectedVendorId, setSelectedVendorId] = useState('');

  useEffect(() => {
    api.get('/api/vendors/').then(res => setVendors(res.data || [])).catch(() => {});
  }, []);

  const { 
    data: rawData = [], 
    totalPages = 1, 
    isError, 
    loadHistory, 
    clearHistory, 
    removeHistoryItem,
    resetCorruptedHistory
  } = useDownloadHistory({ search, reportTypeFilter, page, limit: 15 });

  const historyList = Array.isArray(rawData) ? rawData : [];

  const handleSearch = (val) => { setSearch(val); setPage(1); };

  const handleDownloadReport = async (format) => {
    setIsExporting(true);
    setExportFormat(format);
    try {
      const finalSeries = selectedSeries === 'CUSTOM' ? (customSeries.trim() || 'GST') : selectedSeries;
      const response = await reportsService.downloadSeriesReport({
        reportType: selectedCategory,
        series: finalSeries,
        vendorId: selectedVendorId ? parseInt(selectedVendorId) : undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        format
      });

      const contentDisposition = response.headers['content-disposition'] || '';
      let filename = `Accountant_${selectedCategory}_${format === 'excel' ? 'xlsx' : 'csv'}`;
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

      const typeLabel = `ACCOUNTANT_${selectedCategory.toUpperCase()}${selectedCategory === 'sales' ? `_${finalSeries}` : ''}`;
      saveDownloadMetadata({
        reportType: typeLabel,
        filename,
        rowCount: response.headers['x-row-count'] ? parseInt(response.headers['x-row-count']) : undefined,
        fileFormat: format.toUpperCase(),
        status: 'Completed'
      });

      loadHistory();
    } catch (err) {
      console.error('Export failed:', err);
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
      alert('Failed to generate report: ' + errorMsg);
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

  const currentCategoryObj = REPORT_CATEGORIES.find(c => c.id === selectedCategory) || REPORT_CATEGORIES[0];
  const CategoryIcon = currentCategoryObj.icon;

  const columns = [
    { key: 'reportType', label: 'Report Type', render: (val) => <span className={styles.typeText}>{val ? String(val).replace(/_/g, ' ') : '-'}</span> },
    { key: 'filename', label: 'Filename', render: (val) => <span className={styles.filename}>{val || '-'}</span> },
    { key: 'generatedAt', label: 'Generated At', render: (val) => val ? new Date(val).toLocaleString() : '-' },
    { key: 'rowCount', label: 'Rows', render: (val) => val != null ? val : '-' },
    { key: 'fileFormat', label: 'Format', render: (val) => val || '-' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val || 'Completed'} /> },
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
          <Button variant="secondary" onClick={() => setIsConfirmClearOpen(true)} disabled={historyList.length === 0}>
            <FiTrash2 style={{ marginRight: '8px' }} /> Clear History
          </Button>
        </>
      }
    >
      {/* Universal Accountant Report Hub */}
      <Card noPadding style={{ marginBottom: '24px', overflow: 'visible' }}>
        <div className={styles.seriesSection}>
          
          {/* Category Tabs */}
          <div className={styles.categoryTabs}>
            {REPORT_CATEGORIES.map(cat => {
              const Icon = cat.icon;
              const isActive = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  className={`${styles.categoryTab} ${isActive ? styles.categoryTabActive : ''}`}
                  onClick={() => setSelectedCategory(cat.id)}
                >
                  <Icon size={16} />
                  {cat.label}
                </button>
              );
            })}
          </div>

          {/* Header with Title and Export Buttons */}
          <div className={styles.seriesHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: '#dbeafe', color: '#1d4ed8', padding: '10px', borderRadius: '8px', display: 'flex' }}>
                <CategoryIcon size={22} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#0f172a' }}>
                  {currentCategoryObj.title}
                </h3>
                <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: '#64748b' }}>
                  {currentCategoryObj.desc}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                type="button"
                className={styles.btnDownloadCsv}
                onClick={() => handleDownloadReport('csv')}
                disabled={isExporting}
                title="Download in standard 47-column CSV format with bill totals"
              >
                <FiDownload className={isExporting && exportFormat === 'csv' ? styles.spin : ''} />
                {isExporting && exportFormat === 'csv' ? 'Generating CSV...' : 'Download CSV'}
              </button>
              <button 
                type="button"
                className={styles.btnDownloadExcel}
                onClick={() => handleDownloadReport('excel')}
                disabled={isExporting}
                title="Download styled Microsoft Excel workbook with formulas and bill totals"
              >
                <FiFileText className={isExporting && exportFormat === 'excel' ? styles.spin : ''} />
                {isExporting && exportFormat === 'excel' ? 'Generating Excel...' : 'Download Excel (.xlsx)'}
              </button>
            </div>
          </div>

          {/* Conditional Options: Series Pills for Sales, or Vendor Select for Purchases */}
          {selectedCategory === 'sales' && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Select Invoice / Order Series
              </div>
              <div className={styles.seriesPills}>
                {seriesPresets.map((preset) => (
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
          )}

          {selectedCategory === 'purchases' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className={styles.label}>Filter by Vendor:</span>
              <select 
                className={styles.vendorSelect}
                value={selectedVendorId}
                onChange={e => setSelectedVendorId(e.target.value)}
              >
                <option value="">All Vendors (Consolidated Register)</option>
                {vendors.map(v => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>
          )}

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
          <DataTable
            columns={columns}
            data={historyList}
            emptyMessage="No reports downloaded yet. Generate one above to track it here."
          />
        </div>

        {totalPages > 1 && (
          <TablePagination 
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        )}
      </Card>

      {/* View Metadata Modal */}
      {selectedRecord && (
        <DownloadHistoryModal
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
        />
      )}

      {/* Confirm Clear Modal */}
      <ConfirmationDialog
        isOpen={isConfirmClearOpen}
        title="Clear Download History"
        message="Are you sure you want to clear your local download history? This action cannot be undone."
        confirmLabel="Clear All"
        cancelLabel="Cancel"
        onConfirm={() => {
          clearHistory();
          setIsConfirmClearOpen(false);
        }}
        onCancel={() => setIsConfirmClearOpen(false)}
      />
    </PageContainer>
  );
};

export default DownloadCentre;

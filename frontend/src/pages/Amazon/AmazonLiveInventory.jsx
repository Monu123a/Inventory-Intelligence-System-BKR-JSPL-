import React, { useState, useRef } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import Button from '../../components/forms/Button';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import { 
  FiRefreshCw, 
  FiCloudLightning, 
  FiAlertTriangle, 
  FiCheckCircle, 
  FiClock, 
  FiBox, 
  FiLayers, 
  FiShield,
  FiSearch,
  FiTruck,
  FiUploadCloud,
  FiFileText
} from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { amazonService } from '../../services/amazonService';
import styles from './Amazon.module.css';

const AmazonLiveInventory = () => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [networkFilter, setNetworkFilter] = useState('ALL');
  const [activeTab, setActiveTab] = useState('allocations');
  const [backfillMode, setBackfillMode] = useState(false);
  const [reportDaysBack, setReportDaysBack] = useState(7);
  const [selectedFile, setSelectedFile] = useState(null);

  // 1. Fetch Sync Telemetry & Health Status
  const { 
    data: syncStatus, 
    isLoading: loadingStatus,
    refetch: refetchStatus 
  } = useQuery({
    queryKey: ['amazon', 'sync-status'],
    queryFn: amazonService.getSyncStatus,
    refetchInterval: (query) => {
      return query?.state?.data?.status === 'IN_PROGRESS' ? 3000 : 30000;
    },
  });

  const isSyncInProgress = syncStatus?.status === 'IN_PROGRESS';

  // 2. Fetch Live Soft Allocations
  const { 
    data: rawAllocations = [], 
    isLoading: loadingAllocations, 
    error: allocationsError,
    refetch: refetchAllocations
  } = useQuery({
    queryKey: ['amazon', 'live-inventory'],
    queryFn: amazonService.getLiveInventory,
    refetchInterval: isSyncInProgress ? 3000 : false,
  });

  // 3. Fetch DLQ / Quarantined SKUs
  const {
    data: dlqRecords = [],
    isLoading: loadingDlq,
    refetch: refetchDlq
  } = useQuery({
    queryKey: ['amazon', 'dlq'],
    queryFn: () => amazonService.getDlqRecords(100),
    refetchInterval: isSyncInProgress ? 5000 : false,
  });

  // 4. Fetch FC Inventory Summary
  const {
    data: fcSummaries = [],
    isLoading: loadingFcSummary,
    refetch: refetchFcSummary
  } = useQuery({
    queryKey: ['amazon', 'fc-summary'],
    queryFn: amazonService.getFcInventorySummary,
  });

  // 5. Trigger Orders Sync Mutation
  const syncMutation = useMutation({
    mutationFn: (options) => amazonService.triggerSync(options),
    onSuccess: (data) => {
      toast.success(data?.message || 'Amazon sync initiated!');
      queryClient.invalidateQueries({ queryKey: ['amazon', 'sync-status'] });
      queryClient.invalidateQueries({ queryKey: ['amazon', 'live-inventory'] });
      queryClient.invalidateQueries({ queryKey: ['amazon', 'dlq'] });
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to trigger Amazon sync');
    }
  });

  // 6. Request FC Shipment Report Mutation (SP-API)
  const requestShipmentsMutation = useMutation({
    mutationFn: (params) => amazonService.requestFcShipments(params),
    onSuccess: (data) => {
      toast.success(data?.message || 'Amazon shipment report requested!');
      queryClient.invalidateQueries({ queryKey: ['amazon', 'fc-summary'] });
      queryClient.invalidateQueries({ queryKey: ['amazon', 'live-inventory'] });
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to request Amazon shipment report');
    }
  });

  // 7. Upload FC Shipment Report Mutation
  const uploadShipmentsMutation = useMutation({
    mutationFn: (formData) => amazonService.uploadFcShipments(formData),
    onSuccess: (data) => {
      const details = data?.details || {};
      const breakdown = details.fc_breakdown || {};
      const breakdownStr = Object.entries(breakdown).map(([fc, qty]) => `${fc}: ${qty}`).join(', ');
      toast.success(`Deducted ${details.units_deducted || 0} units across FCs (${breakdownStr || 'None'})!`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      queryClient.invalidateQueries({ queryKey: ['amazon', 'fc-summary'] });
      queryClient.invalidateQueries({ queryKey: ['amazon', 'live-inventory'] });
      queryClient.invalidateQueries({ queryKey: ['amazon', 'dlq'] });
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed processing uploaded shipment report');
    }
  });

  const handleSyncClick = () => {
    syncMutation.mutate({
      backfill: backfillMode,
      async_mode: true
    });
  };

  const handleRequestShipmentsClick = () => {
    requestShipmentsMutation.mutate({
      days_back: reportDaysBack,
      async_mode: true
    });
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleProcessUploadedFile = () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);
    uploadShipmentsMutation.mutate(formData);
  };

  const handleRefreshAll = () => {
    refetchStatus();
    refetchAllocations();
    refetchDlq();
    refetchFcSummary();
  };

  // Filter allocations
  const allocations = Array.isArray(rawAllocations) ? rawAllocations : [];
  const filteredAllocations = allocations.filter((item) => {
    const matchesSearch = !searchTerm || item.sku.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesNetwork = networkFilter === 'ALL' || item.network === networkFilter;
    return matchesSearch && matchesNetwork;
  });

  // Calculate totals
  const totalSoftReserved = allocations.reduce((acc, curr) => acc + (curr.pending_qty || 0), 0);

  const allocationColumns = [
    { key: 'sku', label: 'SKU' },
    { key: 'network_badge', label: 'Network' },
    { key: 'allocated_qty', label: 'Total Allocated' },
    { key: 'reconciled_qty', label: 'Reconciled (Shipped)' },
    { key: 'pending_qty', label: 'Soft Reserved (Active)' },
    { key: 'active_orders', label: 'Open Orders' },
  ];

  const fcColumns = [
    { key: 'fc_code_badge', label: 'FC Warehouse' },
    { key: 'name', label: 'Facility Name' },
    { key: 'total_skus', label: 'Active SKUs' },
    { key: 'physical_units', label: 'Physical Stock (Current)' },
    { key: 'active_allocations', label: 'Active AFN Reservations' },
    { key: 'available_units', label: 'Available Units' },
  ];

  const dlqColumns = [
    { key: 'order_id', label: 'Amazon Order ID' },
    { key: 'sku_details', label: 'Quarantined Item / SKU' },
    { key: 'error_message', label: 'Quarantine Reason' },
    { key: 'created_at', label: 'Detected At' },
  ];

  const formatDateTime = (isoStr) => {
    if (!isoStr) return 'Never';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <PageContainer title="Amazon Live Inventory & Order Sync">
      <div className={styles.container}>
        {/* Header Actions Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#111827', fontWeight: 600 }}>
              Live SP-API Inventory Synchronization & FC Deduction
            </h2>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: '#6b7280' }}>
              Two-phase soft allocation engine protecting offline POS, with automated FC-wise shipment deduction.
            </p>
          </div>

          <div className={styles.headerActions}>
            <label className={styles.checkboxLabel} title="Fetch all historical orders starting August 1, 2026">
              <input 
                type="checkbox" 
                checked={backfillMode} 
                onChange={(e) => setBackfillMode(e.target.checked)} 
                disabled={isSyncInProgress || syncMutation.isPending}
              />
              <span>Full Backfill (Aug 1 - Now)</span>
            </label>

            <Button
              variant="primary"
              onClick={handleSyncClick}
              isLoading={isSyncInProgress || syncMutation.isPending}
              disabled={isSyncInProgress || syncMutation.isPending}
            >
              <FiCloudLightning style={{ marginRight: '0.5rem' }} />
              {isSyncInProgress ? 'Syncing SP-API...' : 'Sync Amazon Orders'}
            </Button>

            <Button
              variant="secondary"
              onClick={handleRefreshAll}
              title="Refresh Dashboard"
            >
              <FiRefreshCw />
            </Button>
          </div>
        </div>

        {/* Telemetry & Metrics Cards */}
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <div className={styles.metricHeader}>
              <span>SP-API Sync Status</span>
              {syncStatus?.status === 'SUCCESS' && <FiCheckCircle color="#059669" />}
              {syncStatus?.status === 'IN_PROGRESS' && <FiClock color="#2563eb" />}
              {syncStatus?.status === 'FAILED' && <FiAlertTriangle color="#dc2626" />}
            </div>
            <div className={styles.metricValue}>
              <span className={`
                ${styles.badge} 
                ${syncStatus?.status === 'SUCCESS' ? styles.badgeSuccess : ''}
                ${syncStatus?.status === 'IN_PROGRESS' ? styles.badgeProgress : ''}
                ${syncStatus?.status === 'FAILED' ? styles.badgeFailed : ''}
                ${!syncStatus?.status || syncStatus?.status === 'NEVER_RUN' ? styles.badgeNeutral : ''}
              `}>
                {syncStatus?.status || 'IDLE'}
              </span>
            </div>
            <div className={styles.metricSubtitle}>
              Last run: {formatDateTime(syncStatus?.last_sync_end || syncStatus?.last_sync_start)}
            </div>
          </div>

          <div className={styles.metricCard}>
            <div className={styles.metricHeader}>
              <span>Active Soft Reservations</span>
              <FiShield color="#4f46e5" />
            </div>
            <div className={styles.metricValue}>
              {totalSoftReserved}
              <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280' }}>units</span>
            </div>
            <div className={styles.metricSubtitle}>
              Across {syncStatus?.active_orders_count ?? 0} open Amazon orders
            </div>
          </div>

          <div className={styles.metricCard}>
            <div className={styles.metricHeader}>
              <span>Amazon Fulfillment Centers</span>
              <FiTruck color="#0284c7" />
            </div>
            <div className={styles.metricValue}>
              {fcSummaries.length}
              <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280' }}>FC warehouses</span>
            </div>
            <div className={styles.metricSubtitle}>
              BLR8, BOM7, MAA4, DEL4 & more
            </div>
          </div>

          <div className={styles.metricCard}>
            <div className={styles.metricHeader}>
              <span>Quarantined SKUs (DLQ)</span>
              <FiAlertTriangle color={syncStatus?.dlq_count > 0 ? '#d97706' : '#9ca3af'} />
            </div>
            <div className={styles.metricValue}>
              {syncStatus?.dlq_count ?? dlqRecords.length}
              <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280' }}>items</span>
            </div>
            <div className={styles.metricSubtitle}>
              {syncStatus?.dlq_count > 0 ? 'Requires SKU review' : 'Zero catalog mismatches'}
            </div>
          </div>
        </div>

        {/* Informational Banner */}
        <div className={styles.infoBanner}>
          <FiShield size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Automated Two-Phase Inventory Engine:</strong>
            <div style={{ marginTop: '0.25rem', lineHeight: 1.4 }}>
              1. <strong>Live Orders (SP-API Orders):</strong> Immediately soft-reserves stock to protect offline POS from overselling.<br />
              2. <strong>Shipment Reports (SP-API Reports):</strong> Identifies the exact physical Amazon FC (<code>BLR8</code>, <code>BOM7</code>, etc.) and permanently deducts inventory from that specific FC warehouse ledger.
            </div>
          </div>
        </div>

        {/* Tabs for Allocations vs FC Reconciliation vs DLQ */}
        <Card noPadding>
          <div className={styles.tabsContainer} style={{ padding: '0 1rem', margin: 0 }}>
            <button
              className={`${styles.tabButton} ${activeTab === 'allocations' ? styles.tabButtonActive : ''}`}
              onClick={() => setActiveTab('allocations')}
            >
              <FiBox />
              <span>Live Soft Allocations</span>
              <span className={styles.tabCount}>{filteredAllocations.length}</span>
            </button>
            <button
              className={`${styles.tabButton} ${activeTab === 'fc_reconciliation' ? styles.tabButtonActive : ''}`}
              onClick={() => setActiveTab('fc_reconciliation')}
            >
              <FiTruck />
              <span>FC Inventory & Shipment Deduction</span>
              <span className={styles.tabCount}>{fcSummaries.length}</span>
            </button>
            <button
              className={`${styles.tabButton} ${activeTab === 'dlq' ? styles.tabButtonActive : ''}`}
              onClick={() => setActiveTab('dlq')}
            >
              <FiAlertTriangle />
              <span>Quarantined Items (DLQ)</span>
              <span className={styles.tabCount}>{dlqRecords.length}</span>
            </button>
          </div>

          {/* TAB 1: ALLOCATIONS */}
          {activeTab === 'allocations' && (
            <>
              {/* Filter and Search Bar */}
              <div className={styles.filterBar}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '260px' }}>
                  <FiSearch color="#9ca3af" />
                  <input
                    type="text"
                    placeholder="Search by SKU (e.g. LG0831)..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className={styles.searchInput}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.875rem', color: '#4b5563', fontWeight: 500 }}>Network:</span>
                  <select
                    value={networkFilter}
                    onChange={(e) => setNetworkFilter(e.target.value)}
                    className={styles.filterSelect}
                  >
                    <option value="ALL">All Networks</option>
                    <option value="MFN">MFN (Central Warehouse)</option>
                    <option value="AFN">AFN (Amazon FCs)</option>
                  </select>
                </div>
              </div>

              {/* Allocations Table */}
              <div style={{ overflowX: 'auto' }}>
                <DataTable>
                  <TableHeader columns={allocationColumns} />
                  <tbody>
                    {loadingAllocations ? (
                      <tr>
                        <td colSpan={allocationColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#6b7280' }}>
                          <FiClock style={{ display: 'inline', marginRight: '0.5rem' }} />
                          Loading live allocations...
                        </td>
                      </tr>
                    ) : allocationsError ? (
                      <tr>
                        <td colSpan={allocationColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#dc2626' }}>
                          Failed to load allocations: {allocationsError.message}
                        </td>
                      </tr>
                    ) : filteredAllocations.length === 0 ? (
                      <tr>
                        <td colSpan={allocationColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#6b7280' }}>
                          No soft allocations matching the selected filters.
                        </td>
                      </tr>
                    ) : (
                      filteredAllocations.map((row, idx) => {
                        const rowData = {
                          ...row,
                          sku: <strong style={{ color: '#111827' }}>{row.sku}</strong>,
                          network_badge: (
                            <span className={`${styles.badge} ${row.network === 'MFN' ? styles.badgeMfn : styles.badgeAfn}`}>
                              {row.network === 'MFN' ? 'MFN (Local WH)' : 'AFN (Amazon FC)'}
                            </span>
                          ),
                          allocated_qty: <span style={{ fontWeight: 500 }}>{row.allocated_qty}</span>,
                          reconciled_qty: <span style={{ color: '#059669', fontWeight: 500 }}>{row.reconciled_qty}</span>,
                          pending_qty: (
                            <span style={{ color: '#d97706', fontWeight: 700 }}>
                              {row.pending_qty}
                            </span>
                          ),
                          active_orders: (
                            <span style={{ color: '#4b5563' }}>
                              {row.active_orders} orders
                            </span>
                          )
                        };
                        return <TableRow key={idx} row={rowData} columns={allocationColumns} />;
                      })
                    )}
                  </tbody>
                </DataTable>
              </div>
            </>
          )}

          {/* TAB 2: FC RECONCILIATION */}
          {activeTab === 'fc_reconciliation' && (
            <div>
              {/* Action Controls for Automated Pull & File Upload */}
              <div className={styles.actionGrid}>
                {/* Action 1: Automated SP-API Pull */}
                <div className={styles.actionCard}>
                  <div>
                    <h4 style={{ margin: '0 0 0.5rem 0', color: '#111827', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FiCloudLightning color="#2563eb" />
                      <span>Request Amazon Shipment Report</span>
                    </h4>
                    <p style={{ margin: 0, fontSize: '0.8125rem', color: '#6b7280', lineHeight: 1.4 }}>
                      Calls Amazon SP-API Reports to fetch the <code>GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL</code> file, 
                      matches physical FCs (<code>BLR8</code>, <code>BOM7</code>, etc.), and permanently deducts inventory.
                    </p>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1rem' }}>
                    <select
                      value={reportDaysBack}
                      onChange={(e) => setReportDaysBack(Number(e.target.value))}
                      className={styles.filterSelect}
                      style={{ flex: 1 }}
                    >
                      <option value={7}>Past 7 Days</option>
                      <option value={14}>Past 14 Days</option>
                      <option value={30}>Past 30 Days</option>
                      <option value={60}>Past 60 Days</option>
                    </select>

                    <Button
                      variant="primary"
                      onClick={handleRequestShipmentsClick}
                      isLoading={requestShipmentsMutation.isPending}
                      disabled={requestShipmentsMutation.isPending}
                    >
                      Request & Deduct
                    </Button>
                  </div>
                </div>

                {/* Action 2: Manual File Upload */}
                <div className={styles.actionCard}>
                  <div>
                    <h4 style={{ margin: '0 0 0.5rem 0', color: '#111827', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FiUploadCloud color="#059669" />
                      <span>Upload Amazon Report File (.csv / .tsv)</span>
                    </h4>
                    <p style={{ margin: 0, fontSize: '0.8125rem', color: '#6b7280', lineHeight: 1.4 }}>
                      Already downloaded an Amazon Fulfilled Shipments or Settlement Report from Seller Central? 
                      Upload it here for instant FC-wise deduction.
                    </p>
                  </div>

                  <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      onChange={handleFileUpload} 
                      accept=".csv,.tsv,.txt,.xlsx,.xls"
                      style={{ fontSize: '0.8125rem', flex: 1 }}
                    />
                    <Button
                      variant="secondary"
                      onClick={handleProcessUploadedFile}
                      disabled={!selectedFile || uploadShipmentsMutation.isPending}
                      isLoading={uploadShipmentsMutation.isPending}
                    >
                      <FiFileText style={{ marginRight: '0.375rem' }} />
                      Process File
                    </Button>
                  </div>
                </div>
              </div>

              {/* FC Warehouses Live Stock Table */}
              <div style={{ padding: '0 1rem 0.5rem 1rem' }}>
                <h4 style={{ margin: '1rem 0 0.5rem 0', color: '#374151', fontSize: '0.9375rem' }}>
                  Registered Amazon Fulfillment Centers (Physical Inventory)
                </h4>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <DataTable>
                  <TableHeader columns={fcColumns} />
                  <tbody>
                    {loadingFcSummary ? (
                      <tr>
                        <td colSpan={fcColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#6b7280' }}>
                          Loading FC inventory summaries...
                        </td>
                      </tr>
                    ) : fcSummaries.length === 0 ? (
                      <tr>
                        <td colSpan={fcColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#6b7280' }}>
                          No Amazon FC warehouses mapped yet.
                        </td>
                      </tr>
                    ) : (
                      fcSummaries.map((fc, idx) => {
                        const rowData = {
                          ...fc,
                          fc_code_badge: (
                            <span style={{ 
                              padding: '0.25rem 0.5rem', 
                              backgroundColor: '#e0e7ff', 
                              color: '#3730a3', 
                              borderRadius: '0.25rem',
                              fontWeight: 700 
                            }}>
                              {fc.fc_code}
                            </span>
                          ),
                          name: <span style={{ fontWeight: 500, color: '#111827' }}>{fc.name}</span>,
                          total_skus: <span>{fc.total_skus} SKUs</span>,
                          physical_units: (
                            <span style={{ fontWeight: 600, color: fc.physical_units < 0 ? '#dc2626' : '#111827' }}>
                              {fc.physical_units} units
                            </span>
                          ),
                          active_allocations: (
                            <span style={{ color: '#d97706', fontWeight: 600 }}>
                              {fc.active_allocations} reserved
                            </span>
                          ),
                          available_units: (
                            <span style={{ fontWeight: 700, color: fc.available_units < 0 ? '#dc2626' : '#059669' }}>
                              {fc.available_units} units
                            </span>
                          )
                        };
                        return <TableRow key={idx} row={rowData} columns={fcColumns} />;
                      })
                    )}
                  </tbody>
                </DataTable>
              </div>
            </div>
          )}

          {/* TAB 3: DLQ */}
          {activeTab === 'dlq' && (
            <div>
              {/* Isolation Rule Notice */}
              <div className={styles.warningBanner}>
                <FiAlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <strong>Strict SKU Isolation Active:</strong>
                  <div style={{ marginTop: '0.25rem', lineHeight: 1.4 }}>
                    Per inventory integrity rules, variants with suffixes (such as <code>LG1151-1</code> or <code>LG0637-1</code>) 
                    are never merged with base SKUs (<code>LG1151</code>). Any order item referencing an unmapped SKU is safely 
                    quarantined in this Dead Letter Queue so it can be added to the product master list.
                  </div>
                </div>
              </div>

              {/* DLQ Table */}
              <div style={{ overflowX: 'auto' }}>
                <DataTable>
                  <TableHeader columns={dlqColumns} />
                  <tbody>
                    {loadingDlq ? (
                      <tr>
                        <td colSpan={dlqColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#6b7280' }}>
                          Loading quarantined items...
                        </td>
                      </tr>
                    ) : dlqRecords.length === 0 ? (
                      <tr>
                        <td colSpan={dlqColumns.length} style={{ textAlign: 'center', padding: '2.5rem', color: '#059669' }}>
                          <FiCheckCircle style={{ display: 'inline', marginRight: '0.5rem' }} />
                          No quarantined items! All Amazon SKUs matched the product catalog.
                        </td>
                      </tr>
                    ) : (
                      dlqRecords.map((item, idx) => {
                        const payloadItem = item.payload?.item || item.payload || {};
                        const rowData = {
                          order_id: (
                            <div>
                              <strong style={{ color: '#111827' }}>{item.order_id}</strong>
                              <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                                Channel: {item.payload?.channel || 'Unknown'} {item.payload?.fc ? `(FC: ${item.payload.fc})` : ''}
                              </div>
                            </div>
                          ),
                          sku_details: (
                            <div>
                              <span style={{ 
                                display: 'inline-block',
                                padding: '0.125rem 0.5rem', 
                                backgroundColor: '#fee2e2', 
                                color: '#991b1b', 
                                borderRadius: '0.25rem',
                                fontWeight: 600,
                                fontSize: '0.8125rem'
                              }}>
                                {payloadItem.sku || 'N/A'}
                              </span>
                              <div style={{ fontSize: '0.75rem', color: '#4b5563', marginTop: '0.25rem' }}>
                                {payloadItem.title ? `${payloadItem.title.substring(0, 50)}...` : 'No title'} (Qty: {payloadItem.quantity || 1})
                              </div>
                            </div>
                          ),
                          error_message: (
                            <span style={{ color: '#dc2626', fontSize: '0.875rem' }}>
                              {item.error_message}
                            </span>
                          ),
                          created_at: (
                            <span style={{ fontSize: '0.8125rem', color: '#6b7280' }}>
                              {formatDateTime(item.created_at)}
                            </span>
                          )
                        };
                        return <TableRow key={idx} row={rowData} columns={dlqColumns} />;
                      })
                    )}
                  </tbody>
                </DataTable>
              </div>
            </div>
          )}
        </Card>
      </div>
    </PageContainer>
  );
};

export default AmazonLiveInventory;

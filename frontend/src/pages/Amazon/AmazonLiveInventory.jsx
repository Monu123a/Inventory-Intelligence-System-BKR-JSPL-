import React, { useState } from 'react';
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
  FiSearch
} from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { amazonService } from '../../services/amazonService';
import styles from './Amazon.module.css';

const AmazonLiveInventory = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [networkFilter, setNetworkFilter] = useState('ALL');
  const [activeTab, setActiveTab] = useState('allocations');
  const [backfillMode, setBackfillMode] = useState(false);

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

  // 4. Trigger Sync Mutation
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

  const handleSyncClick = () => {
    syncMutation.mutate({
      backfill: backfillMode,
      async_mode: true
    });
  };

  const handleRefreshAll = () => {
    refetchStatus();
    refetchAllocations();
    refetchDlq();
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
  const totalReconciled = allocations.reduce((acc, curr) => acc + (curr.reconciled_qty || 0), 0);

  const allocationColumns = [
    { key: 'sku', label: 'SKU' },
    { key: 'network_badge', label: 'Network' },
    { key: 'allocated_qty', label: 'Total Allocated' },
    { key: 'reconciled_qty', label: 'Reconciled (Shipped)' },
    { key: 'pending_qty', label: 'Soft Reserved (Active)' },
    { key: 'active_orders', label: 'Open Orders' },
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
              Live SP-API Inventory Synchronization
            </h2>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: '#6b7280' }}>
              Two-phase soft allocation engine protecting offline POS and B2B orders from overselling.
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
              Across {syncStatus?.active_orders_count ?? allocations.reduce((acc, c) => acc + (c.active_orders || 0), 0)} open Amazon orders
            </div>
          </div>

          <div className={styles.metricCard}>
            <div className={styles.metricHeader}>
              <span>Last Sync Telemetry</span>
              <FiLayers color="#0284c7" />
            </div>
            <div className={styles.metricValue}>
              {syncStatus?.orders_processed ?? 0}
              <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280' }}>processed</span>
            </div>
            <div className={styles.metricSubtitle}>
              {syncStatus?.skipped_duplicates ?? 0} skipped (known) • {syncStatus?.failed_items ?? 0} quarantined
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
            <strong>How Soft Allocation Protects Your Inventory:</strong>
            <div style={{ marginTop: '0.25rem', lineHeight: 1.4 }}>
              When a buyer places an order on Amazon, stock is immediately soft-reserved in <code>AmazonLiveAllocation</code>, 
              reducing the available stock displayed in Offline POS and B2B order entry. 
              Once the Amazon Settlement or Dispatch report arrives, the reserved quantity is permanently deducted from physical warehouse inventory.
            </div>
          </div>
        </div>

        {/* Tabs for Allocations vs DLQ */}
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
              className={`${styles.tabButton} ${activeTab === 'dlq' ? styles.tabButtonActive : ''}`}
              onClick={() => setActiveTab('dlq')}
            >
              <FiAlertTriangle />
              <span>Quarantined Items (DLQ)</span>
              <span className={styles.tabCount}>{dlqRecords.length}</span>
            </button>
          </div>

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
                        const payloadItem = item.payload?.item || {};
                        const rowData = {
                          order_id: (
                            <div>
                              <strong style={{ color: '#111827' }}>{item.order_id}</strong>
                              <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                                Channel: {item.payload?.channel || 'Unknown'}
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

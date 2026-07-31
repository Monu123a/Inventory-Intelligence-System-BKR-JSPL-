import React from 'react';
import { Card } from '../../../components/Card/Card';
import { StatusBadge } from '../../../components/StatusBadge/StatusBadge';
import { FiCheckCircle, FiClock, FiDatabase, FiRefreshCw, FiCalendar } from 'react-icons/fi';
import styles from './SystemHealthCard.module.css';

const HealthRow = ({ label, value, icon: Icon, isStatus = false }) => (
  <div className={styles.row}>
    <div className={styles.labelGroup}>
      <Icon className={styles.icon} />
      <span className={styles.label}>{label}</span>
    </div>
    <div className={styles.valueGroup}>
      {isStatus ? (
        <StatusBadge status={value || 'Unknown'} />
      ) : (
        <span className={styles.value}>
          {value ? new Date(value).toLocaleString() : 'Never'}
        </span>
      )}
    </div>
  </div>
);

export const SystemHealthCard = ({ health }) => {
  if (!health) return null;

  return (
    <Card title="System Health" className={styles.healthCard}>
      <div className={styles.list}>
        <HealthRow 
          label="Scheduler Status" 
          value={health.scheduler_status} 
          icon={FiCheckCircle} 
          isStatus={true} 
        />
        
        {/* Enriched Amazon Sync Data */}
        <div className={styles.amazonSyncContainer} style={{ background: 'var(--color-neutral-50)', padding: 'var(--spacing-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', fontWeight: 600 }}>
              <FiRefreshCw color="var(--color-primary)" />
              Amazon Sync Status
            </div>
            <StatusBadge status={health.amazon_sync?.status || 'Unknown'} />
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.75rem', color: 'var(--color-neutral-600)' }}>
            <div><strong>Last Sync:</strong> {health.amazon_sync?.sync_start_time ? new Date(health.amazon_sync.sync_start_time).toLocaleString() : 'Never'}</div>
            <div><strong>Orders:</strong> {health.amazon_sync?.orders_processed || 0}</div>
            <div><strong>Movements:</strong> {health.amazon_sync?.movements_created || 0}</div>
            <div><strong>Skipped:</strong> {health.amazon_sync?.skipped_duplicates || 0}</div>
            <div style={{ color: health.amazon_sync?.failed_items > 0 ? 'var(--color-danger)' : 'inherit' }}>
              <strong>Failed:</strong> {health.amazon_sync?.failed_items || 0}
            </div>
            {health.amazon_sync?.next_token && (
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={health.amazon_sync.next_token}>
                <strong>Token:</strong> {health.amazon_sync.next_token}
              </div>
            )}
          </div>
          
          {health.amazon_sync?.unknown_skus && health.amazon_sync.unknown_skus !== "[]" && (
             <div style={{ marginTop: '8px', background: 'var(--color-warning-50)', color: 'var(--color-warning-900)', padding: '6px', borderRadius: '4px', fontSize: '0.75rem' }}>
               <strong>Unknown SKUs Detected:</strong> 
               <div style={{ fontFamily: 'monospace', marginTop: '4px' }}>
                 {(() => {
                   try {
                     const skus = JSON.parse(health.amazon_sync.unknown_skus);
                     return skus.join(", ");
                   } catch {
                     return health.amazon_sync.unknown_skus;
                   }
                 })()}
               </div>
             </div>
          )}

          {health.amazon_sync?.errors && (
            <div style={{ marginTop: '8px', color: 'var(--color-danger)', fontSize: '0.75rem' }}>
              <strong>Error:</strong> {health.amazon_sync.errors}
            </div>
          )}
        </div>

        <HealthRow 
          label="Last Inventory Upload" 
          value={health.latest_inventory_upload} 
          icon={FiDatabase} 
        />
        <HealthRow 
          label="Last Midnight Snapshot" 
          value={health.last_snapshot_time} 
          icon={FiClock} 
        />
        <HealthRow 
          label="Last Replenishment Report" 
          value={health.last_replenishment_report} 
          icon={FiCalendar} 
        />
      </div>
    </Card>
  );
};

import React from 'react';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import styles from './HistoryDetailsModal.module.css';
import { FiClock, FiBox, FiInfo } from 'react-icons/fi';

export const HistoryDetailsModal = ({ isOpen, onClose, record }) => {
  if (!record) return null;

  const isPositive = record.qty_changed > 0;
  const isNegative = record.qty_changed < 0;
  
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Event Details" maxWidth="600px">
      <div className={styles.container}>
        
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}><FiInfo /> General Information</h4>
          <div className={styles.grid}>
            <div className={styles.field}>
              <span className={styles.label}>Timestamp</span>
              <span className={styles.value}>{new Date(record.timestamp).toLocaleString()}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Event Type (Source)</span>
              <span className={styles.value}>{record.source}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Reference ID</span>
              <span className={styles.value}>{record.reference_id || 'N/A'}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>User</span>
              <span className={styles.value}>System</span> {/* Hardcoded for now as user auth is basic */}
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}><FiBox /> Product Details</h4>
          <div className={styles.grid}>
            <div className={styles.field}>
              <span className={styles.label}>SKU</span>
              <span className={styles.value}>{record.product_sku}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Product Name</span>
              <span className={styles.value}>{record.product_name}</span>
            </div>
            <div className={styles.field}>
              <span className={styles.label}>Warehouse</span>
              <span className={styles.value}>{record.warehouse_name}</span>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}><FiClock /> Inventory Values</h4>
          <div className={styles.qtyGrid}>
            <div className={styles.qtyBox}>
              <span className={styles.qtyLabel}>Quantity Before</span>
              <span className={styles.qtyValue}>{record.qty_before}</span>
            </div>
            <div className={`${styles.qtyBox} ${isPositive ? styles.positive : ''} ${isNegative ? styles.negative : ''}`}>
              <span className={styles.qtyLabel}>Quantity Changed</span>
              <span className={styles.qtyValue}>
                {isPositive ? '+' : ''}{record.qty_changed}
              </span>
            </div>
            <div className={styles.qtyBox}>
              <span className={styles.qtyLabel}>Quantity After</span>
              <span className={styles.qtyValue}>{record.qty_after}</span>
            </div>
          </div>
        </div>

        {record.display_metadata && record.display_metadata.length > 0 && (
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>Metadata</h4>
            <div className={styles.grid}>
              {record.display_metadata.map((meta, i) => (
                <div key={i} className={styles.field}>
                  <span className={styles.label}>{meta.label}</span>
                  <span className={styles.value}>{meta.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className={styles.actions}>
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
      </div>
    </Modal>
  );
};

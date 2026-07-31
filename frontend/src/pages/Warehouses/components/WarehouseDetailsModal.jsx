import React from 'react';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import { StatusBadge } from '../../../components/StatusBadge/StatusBadge';
import { FiMapPin, FiUser, FiPhone, FiMail, FiBox, FiLayers } from 'react-icons/fi';
import styles from './WarehouseDetailsModal.module.css';

export const WarehouseDetailsModal = ({ isOpen, onClose, warehouse }) => {
  if (!warehouse) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Warehouse Details" maxWidth="600px">
      <div className={styles.container}>
        
        <div className={styles.header}>
          <div>
            <h3 className={styles.title}>{warehouse.name}</h3>
            <span className={styles.code}>{warehouse.code}</span>
          </div>
          <StatusBadge status={warehouse.status} />
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>General Information</h4>
          <div className={styles.grid}>
            <div className={styles.field}>
              <FiMapPin className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Address</span>
                <span className={styles.value}>{warehouse.address || 'Not Provided'}</span>
              </div>
            </div>
            <div className={styles.field}>
              <FiUser className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Contact Person</span>
                <span className={styles.value}>{warehouse.contact_person || 'Not Provided'}</span>
              </div>
            </div>
            <div className={styles.field}>
              <FiPhone className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Phone</span>
                <span className={styles.value}>{warehouse.phone_number || 'Not Provided'}</span>
              </div>
            </div>
            <div className={styles.field}>
              <FiMail className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Email</span>
                <span className={styles.value}>{warehouse.email || 'Not Provided'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Operational Summary</h4>
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <FiBox className={styles.summaryIcon} />
              <div className={styles.summaryContent}>
                <span className={styles.summaryValue}>{warehouse.total_products || 0}</span>
                <span className={styles.summaryLabel}>Unique SKUs</span>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <FiLayers className={styles.summaryIcon} />
              <div className={styles.summaryContent}>
                <span className={styles.summaryValue}>{warehouse.total_inventory || 0}</span>
                <span className={styles.summaryLabel}>Total Quantity</span>
              </div>
            </div>
          </div>
          <p className={styles.hint}>Note: Inventory levels are informational. Manage stock via Inventory Management.</p>
        </div>

        <div className={styles.actions}>
          <Button variant="primary" onClick={onClose}>Close Details</Button>
        </div>
      </div>
    </Modal>
  );
};

import React from 'react';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import { StatusBadge } from '../../../components/StatusBadge/StatusBadge';
import { FiFileText, FiClock, FiDatabase, FiSettings, FiHardDrive } from 'react-icons/fi';
import styles from './DownloadHistoryModal.module.css';

export const DownloadHistoryModal = ({ isOpen, onClose, record }) => {
  if (!record) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Download Metadata" maxWidth="600px">
      <div className={styles.container}>
        
        <div className={styles.header}>
          <div>
            <h3 className={styles.title}>{record.filename}</h3>
            <span className={styles.reportType}>{record.reportType?.replace(/_/g, ' ')}</span>
          </div>
          <StatusBadge status={record.status || 'Metadata Only'} />
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>General Information</h4>
          <div className={styles.grid}>
            <div className={styles.field}>
              <FiFileText className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Report Type</span>
                <span className={styles.value}>{record.reportType}</span>
              </div>
            </div>
            <div className={styles.field}>
              <FiClock className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Generated At</span>
                <span className={styles.value}>{new Date(record.generatedAt).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Export Details</h4>
          <div className={styles.grid}>
            <div className={styles.field}>
              <FiDatabase className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Rows Exported</span>
                <span className={styles.value}>{record.rowCount || 0} rows</span>
              </div>
            </div>
            <div className={styles.field}>
              <FiHardDrive className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>File Format</span>
                <span className={styles.value}>{record.fileFormat || 'CSV'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>System Info</h4>
          <div className={styles.grid}>
            <div className={styles.field}>
              <FiSettings className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>Export Version</span>
                <span className={styles.value}>{record.exportVersion || 'Unknown'}</span>
              </div>
            </div>
            <div className={styles.field}>
              <FiSettings className={styles.icon} />
              <div className={styles.fieldContent}>
                <span className={styles.label}>App Version</span>
                <span className={styles.value}>{record.appVersion || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>

        <p className={styles.hint}>
          Note: For security and storage constraints, the actual file blob is not retained across browser sessions. This entry serves as an audit trail of generation.
        </p>

        <div className={styles.actions}>
          <Button variant="primary" onClick={onClose}>Close</Button>
        </div>
      </div>
    </Modal>
  );
};

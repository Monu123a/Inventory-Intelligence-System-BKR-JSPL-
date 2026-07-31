import React from 'react';
import { Card } from '../../../components/Card/Card';
import { StatusBadge } from '../../../components/StatusBadge/StatusBadge';
import Button from '../../../components/forms/Button';
import { useResolveAlert } from '../../../hooks/useDashboard';
import styles from './AlertsPanel.module.css';
import { FiAlertTriangle, FiInfo, FiXCircle } from 'react-icons/fi';

const AlertIcon = ({ severity }) => {
  switch (severity) {
    case 'CRITICAL': return <FiXCircle className={`${styles.icon} ${styles.critical}`} />;
    case 'WARNING': return <FiAlertTriangle className={`${styles.icon} ${styles.warning}`} />;
    default: return <FiInfo className={`${styles.icon} ${styles.info}`} />;
  }
};

export const AlertsPanel = ({ alerts }) => {
  const { mutate: resolveAlert, isPending } = useResolveAlert();

  const handleResolve = (id) => {
    resolveAlert(id);
  };

  return (
    <Card title="Active Alerts" className={styles.panel}>
      {(!alerts || alerts.length === 0) ? (
        <div className={styles.empty}>
          <FiCheckCircle className={styles.emptyIcon} />
          <p>All clear! No active alerts.</p>
        </div>
      ) : (
        <div className={styles.list}>
          {alerts.map(alert => (
            <div key={alert.id} className={`${styles.alertItem} ${styles[alert.severity?.toLowerCase()]}`}>
              <div className={styles.alertContent}>
                <div className={styles.header}>
                  <AlertIcon severity={alert.severity} />
                  <span className={styles.type}>{alert.type}</span>
                  <StatusBadge status={alert.severity} />
                </div>
                <p className={styles.message}>{alert.message}</p>
                <span className={styles.time}>{new Date(alert.timestamp).toLocaleString()}</span>
              </div>
              <div className={styles.actions}>
                <Button 
                  variant="secondary" 
                  size="sm" 
                  onClick={() => handleResolve(alert.id)}
                  isLoading={isPending}
                >
                  Resolve
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

// Assuming FiCheckCircle was used in empty state but not imported
import { FiCheckCircle } from 'react-icons/fi';

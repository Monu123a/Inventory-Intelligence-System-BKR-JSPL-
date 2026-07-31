import React from 'react';
import styles from './StatusBadge.module.css';

export const StatusBadge = ({ status, className = '' }) => {
  const getStatusColor = (st) => {
    const s = st?.toLowerCase() || '';
    if (['success', 'active', 'healthy', 'processed', 'resolved'].includes(s)) return 'success';
    if (['warning', 'low', 'running'].includes(s)) return 'warning';
    if (['danger', 'error', 'failed', 'critical', 'negative'].includes(s)) return 'danger';
    return 'neutral';
  };

  const colorClass = styles[`badge--${getStatusColor(status)}`];

  return (
    <span className={`${styles.badge} ${colorClass} ${className}`}>
      {status}
    </span>
  );
};

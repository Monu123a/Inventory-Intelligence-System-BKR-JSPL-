import React from 'react';
import styles from './ReportSelector.module.css';

const REPORTS = [
  { id: 'LOW_STOCK', label: 'Low Stock' },
  { id: 'NEGATIVE_STOCK', label: 'Negative Stock' },
  { id: 'DAILY_REPLENISHMENT', label: 'Daily Replenishment' },
  { id: 'WAREHOUSE_SUMMARY', label: 'Warehouse Summary' },
  { id: 'INVENTORY_VALUATION', label: 'Inventory Valuation' },
  { id: 'AMAZON_RETURNS', label: 'Amazon Returns' },
  { id: 'DEFECTIVE_INVENTORY', label: 'Defective Inventory' }
];

export const ReportSelector = ({ activeReport, onSelect }) => {
  return (
    <div className={styles.selectorContainer}>
      {REPORTS.map(report => (
        <button
          key={report.id}
          className={`${styles.tabBtn} ${activeReport === report.id ? styles.active : ''}`}
          onClick={() => onSelect(report.id)}
        >
          {report.label}
        </button>
      ))}
    </div>
  );
};

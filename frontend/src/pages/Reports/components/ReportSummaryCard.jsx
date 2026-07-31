import React from 'react';
import styles from './ReportSummaryCard.module.css';
import { FiTrendingUp, FiAlertTriangle, FiDollarSign, FiLayers } from 'react-icons/fi';

const getIconForReport = (title) => {
  const t = title.toLowerCase();
  if (t.includes('valuation')) return <FiDollarSign />;
  if (t.includes('negative') || t.includes('low')) return <FiAlertTriangle />;
  if (t.includes('warehouse')) return <FiLayers />;
  return <FiTrendingUp />;
};

export const ReportSummaryCard = ({ summary }) => {
  if (!summary) return null;

  const icon = getIconForReport(summary.title);

  return (
    <div className={styles.summaryContainer}>
      <div className={styles.header}>
        <div className={styles.iconContainer}>
          {icon}
        </div>
        <h3 className={styles.title}>{summary.title}</h3>
      </div>
      
      <div className={styles.metricsGrid}>
        {summary.metrics.map((metric, idx) => (
          <div key={idx} className={styles.metricBox}>
            <span className={styles.metricLabel}>{metric.label}</span>
            <span className={styles.metricValue}>{metric.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

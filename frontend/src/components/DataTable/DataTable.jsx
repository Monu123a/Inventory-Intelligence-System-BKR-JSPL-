import React from 'react';
import styles from './DataTable.module.css';

export const DataTable = ({ children, className = '' }) => {
  return (
    <div className={`${styles.wrapper} ${className}`}>
      <table className={styles.table}>
        {children}
      </table>
    </div>
  );
};

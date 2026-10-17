import React from 'react';
import styles from './TableRow.module.css';

export const TableRow = ({ children, row, columns, onClick, className = '' }) => {
  if (children) {
    return (
      <tr className={`${styles.tr} ${className}`} onClick={onClick}>
        {children}
      </tr>
    );
  }

  return (
    <tr className={`${styles.tr} ${className}`} onClick={onClick}>
      {(columns || []).map((col, idx) => (
        <td key={col?.key || idx} className={styles.td}>
          {col?.render ? col.render(row?.[col.key], row) : row?.[col?.key]}
        </td>
      ))}
    </tr>
  );
};


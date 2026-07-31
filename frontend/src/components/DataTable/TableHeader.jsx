import React from 'react';
import styles from './TableHeader.module.css';

export const TableHeader = ({ columns }) => {
  return (
    <thead className={styles.thead}>
      <tr>
        {columns.map((col, idx) => (
          <th key={idx} className={styles.th}>
            {col.label}
          </th>
        ))}
      </tr>
    </thead>
  );
};

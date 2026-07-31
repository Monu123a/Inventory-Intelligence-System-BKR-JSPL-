import React from 'react';
import styles from './TableRow.module.css';

export const TableRow = ({ row, columns, onClick }) => {
  return (
    <tr className={styles.tr} onClick={onClick}>
      {columns.map((col, idx) => (
        <td key={idx} className={styles.td}>
          {col.render ? col.render(row[col.key], row) : row[col.key]}
        </td>
      ))}
    </tr>
  );
};

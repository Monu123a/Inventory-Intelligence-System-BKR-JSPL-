import React from 'react';
import styles from './DataTable.module.css';
import { TableHeader } from './TableHeader';
import { TableRow } from './TableRow';
import { TablePagination } from './TablePagination';

export const DataTable = ({ 
  children, 
  columns, 
  data, 
  isLoading, 
  isError, 
  errorMessage = "An error occurred while loading data.",
  emptyMessage = "No records found.",
  noResultsMessage = "No results match your criteria.",
  hasActiveFilters = false,
  onRowClick,
  className = '',
  pagination
}) => {
  // Backwards compatibility for existing tables passing children manually
  if (children) {
    return (
      <div className={`${styles.wrapper} ${className}`}>
        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            {children}
          </table>
        </div>
      </div>
    );
  }

  // New Streamlined API
  const colCount = columns?.length || 1;

  let content;
  if (isLoading) {
    content = <tr><td colSpan={colCount} className={styles.stateCell}>
      <div className={styles.stateContainer}>
        <div className={styles.spinner}></div>
        <span>Loading data...</span>
      </div>
    </td></tr>;
  } else if (isError) {
    content = <tr><td colSpan={colCount} className={styles.stateCell}>
      <div className={`${styles.stateContainer} ${styles.errorState}`}>
        <span>{errorMessage}</span>
      </div>
    </td></tr>;
  } else if (!data || data.length === 0) {
    content = <tr><td colSpan={colCount} className={styles.stateCell}>
      <div className={styles.stateContainer}>
        <span>{hasActiveFilters ? noResultsMessage : emptyMessage}</span>
      </div>
    </td></tr>;
  } else {
    content = data.map((row, idx) => (
      <TableRow 
        key={row.id || idx} 
        row={row} 
        columns={columns} 
        onClick={() => onRowClick && onRowClick(row)} 
      />
    ));
  }

  return (
    <div className={`${styles.wrapper} ${className}`}>
      <div className={styles.tableResponsive}>
        <table className={styles.table}>
          {columns && <TableHeader columns={columns} />}
          <tbody>
            {content}
          </tbody>
        </table>
      </div>
      {pagination && pagination.totalPages > 1 && (
        <div className={styles.paginationWrapper}>
          <TablePagination 
            currentPage={pagination.currentPage} 
            totalPages={pagination.totalPages} 
            onPageChange={pagination.onPageChange} 
          />
        </div>
      )}
    </div>
  );
};

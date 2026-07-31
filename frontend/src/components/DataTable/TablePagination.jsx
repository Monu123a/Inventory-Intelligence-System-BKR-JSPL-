import React from 'react';
import styles from './TablePagination.module.css';

export const TablePagination = ({ currentPage, totalPages, onPageChange }) => {
  return (
    <div className={styles.pagination}>
      <button 
        className={styles.pageBtn}
        onClick={(e) => {
          e.preventDefault();
          console.log("Prev clicked, new page:", currentPage - 1);
          onPageChange(currentPage - 1);
        }}
        disabled={currentPage <= 1}
      >
        Previous
      </button>
      <span className={styles.info}>
        Page {currentPage} of {totalPages || 1}
      </span>
      <button 
        className={styles.pageBtn}
        onClick={(e) => {
          e.preventDefault();
          console.log("Next clicked, new page:", currentPage + 1);
          onPageChange(currentPage + 1);
        }}
        disabled={currentPage >= totalPages}
      >
        Next
      </button>
    </div>
  );
};

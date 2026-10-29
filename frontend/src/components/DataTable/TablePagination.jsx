import React from 'react';
import styles from './TablePagination.module.css';

export const TablePagination = ({ currentPage, totalPages, onPageChange }) => {
  const pages = React.useMemo(() => {
    const total = totalPages || 1;
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    const current = Math.min(Math.max(1, currentPage), total);
    const result = [];
    
    // Always include page 1
    result.push(1);

    if (current > 3) {
      result.push('...');
    }

    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);

    for (let i = start; i <= end; i++) {
      result.push(i);
    }

    if (current < total - 2) {
      result.push('...');
    }

    // Always include last page
    if (total > 1) {
      result.push(total);
    }

    return result;
  }, [currentPage, totalPages]);

  return (
    <div className={styles.pagination}>
      <button 
        type="button"
        className={styles.pageBtn}
        onClick={(e) => {
          e.preventDefault();
          if (currentPage > 1) onPageChange(currentPage - 1);
        }}
        disabled={currentPage <= 1}
      >
        Previous
      </button>

      <div className={styles.pageNumberGroup}>
        {pages.map((p, idx) => {
          if (p === '...') {
            return (
              <span key={`ellipsis-${idx}`} className={styles.ellipsis}>
                ...
              </span>
            );
          }
          const isActive = p === currentPage;
          return (
            <button
              key={p}
              type="button"
              className={`${styles.pageBtn} ${isActive ? styles.activePageBtn : ''}`}
              onClick={(e) => {
                e.preventDefault();
                onPageChange(p);
              }}
            >
              {p}
            </button>
          );
        })}
      </div>

      <button 
        type="button"
        className={styles.pageBtn}
        onClick={(e) => {
          e.preventDefault();
          if (currentPage < totalPages) onPageChange(currentPage + 1);
        }}
        disabled={currentPage >= (totalPages || 1)}
      >
        Next
      </button>
    </div>
  );
};

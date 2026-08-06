import React, { useState, useEffect } from 'react';
import { FiSearch, FiRefreshCw, FiDownload, FiPrinter, FiFilter } from 'react-icons/fi';
import Button from '../forms/Button';
import styles from './ReportToolbar.module.css';
import api from '../../services/api'; // for contextual export

export const ReportToolbar = ({
  searchPlaceholder = "Search...",
  searchValue,
  onSearchChange,
  
  // Date Range
  showDateRange = true,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,

  // Custom filters (array of objects { label, value, options: [{label, value}], onChange })
  customFilters = [],
  
  // Actions
  onRefresh,
  isRefreshing = false,
  
  onPrint,
  
  // Contextual Export functionality
  exportEndpoint,
  exportParams = {},
  exportFileName = "export.csv"
}) => {

  const [isExporting, setIsExporting] = useState(false);
  const [debouncedSearch, setDebouncedSearch] = useState(searchValue);

  // Handle search debounce
  useEffect(() => {
    const handler = setTimeout(() => {
      if (onSearchChange) onSearchChange(debouncedSearch);
    }, 500);
    return () => clearTimeout(handler);
  }, [debouncedSearch, onSearchChange]);

  const handleExport = async () => {
    if (!exportEndpoint) {
      console.warn("Export requested but no exportEndpoint provided.");
      return;
    }
    
    setIsExporting(true);
    try {
      // Build final params exactly matching the current filters applied
      const finalParams = {
        ...exportParams,
        search: debouncedSearch || undefined,
        date_from: startDate || undefined,
        date_to: endDate || undefined,
      };

      const response = await api.get(exportEndpoint, {
        params: finalParams,
        responseType: 'blob'
      });

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', exportFileName);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error("Export failed:", err);
      alert("Failed to export report.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className={styles.toolbarContainer}>
      <div className={styles.filtersSection}>
        {/* Search */}
        {onSearchChange !== undefined && (
          <div className={styles.searchWrapper}>
            <FiSearch className={styles.searchIcon} />
            <input 
              type="text"
              className={styles.searchInput}
              placeholder={searchPlaceholder}
              value={debouncedSearch}
              onChange={(e) => setDebouncedSearch(e.target.value)}
            />
          </div>
        )}

        {/* Date Range */}
        {showDateRange && (
          <div className={styles.dateRangeWrapper}>
            <input 
              type="date"
              className={styles.dateInput}
              value={startDate || ''}
              onChange={(e) => onStartDateChange && onStartDateChange(e.target.value)}
              title="Start Date"
            />
            <span className={styles.dateSeparator}>to</span>
            <input 
              type="date"
              className={styles.dateInput}
              value={endDate || ''}
              onChange={(e) => onEndDateChange && onEndDateChange(e.target.value)}
              title="End Date"
            />
          </div>
        )}

        {/* Custom Dropdown Filters */}
        {customFilters.map((filter, idx) => (
          <select 
            key={idx}
            className={styles.filterSelect}
            value={filter.value}
            onChange={(e) => filter.onChange(e.target.value)}
            title={filter.label}
          >
            {filter.options.map((opt, oIdx) => (
              <option key={oIdx} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        ))}
      </div>

      <div className={styles.actionsSection}>
        {onRefresh && (
          <Button variant="secondary" onClick={onRefresh} isLoading={isRefreshing} title="Refresh Data">
            <FiRefreshCw />
          </Button>
        )}
        
        {exportEndpoint && (
          <Button variant="secondary" onClick={handleExport} isLoading={isExporting} title="Export to CSV">
            <FiDownload /> Export
          </Button>
        )}
        
        {onPrint && (
          <Button variant="secondary" onClick={onPrint} title="Print Report">
            <FiPrinter /> Print
          </Button>
        )}
      </div>
    </div>
  );
};

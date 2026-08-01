import React from 'react';
import { SearchBar } from '../../../components/forms/SearchBar';
import Button from '../../../components/forms/Button';
import { FiDownload, FiRefreshCw } from 'react-icons/fi';
import styles from './HistoryFilters.module.css';

export const HistoryFilters = ({
  setSearch,
  dateRange, setDateRange,
  warehouseId, setWarehouseId,
  sourceFilter, setSourceFilter,
  skuFilter, setSkuFilter,
  onRefresh, isPending,
  onExport, disableExport
}) => {
  return (
    <div className={styles.filtersContainer}>
      <div className={styles.topRow}>
        <SearchBar onSearch={setSearch} placeholder="Search SKU, Product Name, Ref ID..." />
        
        <div className={styles.actions}>
          <Button variant="secondary" onClick={onRefresh} isLoading={isPending}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
          </Button>
          <Button variant="primary" onClick={onExport} disabled={disableExport || isPending}>
            <FiDownload style={{ marginRight: '8px' }} /> Export CSV
          </Button>
        </div>
      </div>

      <div className={styles.bottomRow}>
        <div className={styles.filterGroup}>
          <label>Date Range</label>
          <div className={styles.dateInputs}>
            <input 
              type="date" 
              className={styles.input} 
              value={dateRange.start} 
              onChange={e => setDateRange(prev => ({ ...prev, start: e.target.value }))} 
            />
            <span>to</span>
            <input 
              type="date" 
              className={styles.input} 
              value={dateRange.end} 
              onChange={e => setDateRange(prev => ({ ...prev, end: e.target.value }))} 
            />
          </div>
        </div>

        <div className={styles.filterGroup}>
          <label>Warehouse</label>
          <select className={styles.select} value={warehouseId} onChange={e => setWarehouseId(e.target.value)}>
            <option value="">All Warehouses</option>
            <option value="1">Main Warehouse</option>
            <option value="2">Secondary Warehouse</option>
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label>Event Type</label>
          <select className={styles.select} value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
            <option value="">All Event Types</option>
            <option value="Amazon">Amazon Order</option>
            <option value="Upload">Inventory Upload</option>
            <option value="Manual">Manual Adjustment</option>
            <option value="Transfer In">Transfer In</option>
            <option value="Transfer Out">Transfer Out</option>
          </select>
        </div>
        
        <div className={styles.filterGroup}>
          <label>Filter by SKU</label>
          <input 
            type="text" 
            className={styles.input} 
            placeholder="e.g. SKU-123" 
            value={skuFilter}
            onChange={e => setSkuFilter(e.target.value)}
          />
        </div>
      </div>
    </div>
  );
};

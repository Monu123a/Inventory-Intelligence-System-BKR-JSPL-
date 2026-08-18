import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import { StatusBadge } from '../../components/StatusBadge/StatusBadge';
import useCompanyStore from '../../stores/useCompanyStore';
import Button from '../../components/forms/Button';
import { SearchBar } from '../../components/forms/SearchBar';
import { UploadModal } from './components/UploadModal';
import { AdjustmentModal } from './components/AdjustmentModal';
import { useInventory, useManualAdjustment } from '../../hooks/useInventory';
import { ROUTES } from '../../constants/routes';
import { FiUploadCloud, FiRefreshCw, FiEdit3, FiClock } from 'react-icons/fi';
import styles from './Inventory.module.css';

const Inventory = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [warehouseFilter, setWarehouseFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [adjustingItem, setAdjustingItem] = useState(null);
  const { currentCompany } = useCompanyStore();
  const isBkr = currentCompany?.code === 'BKR';

  const { data: inventoryData, totalPages, isPending, refetch, warehouses } = useInventory({
    search, warehouseId: warehouseFilter, filterStatus: statusFilter, page, limit: 15
  });

  const adjustMutation = useManualAdjustment();

  const handleSearch = useCallback((val) => { setSearch(val); setPage(1); }, []);

  const handleAdjustmentSubmit = (data) => {
    adjustMutation.mutate(data, {
      onSuccess: () => setAdjustingItem(null)
    });
  };

  const columns = [
    { key: 'product?.sku', label: 'SKU', render: (val, row) => row.product?.sku || val },
    { key: 'product_name', label: 'Product Name' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { 
      key: 'current_qty', 
      label: 'On Hand', 
      render: (val) => <span className={styles.qtyText}>{val}</span>
    },
    { key: 'reserved_qty', label: 'Reserved' },
    { 
      key: 'available_qty', 
      label: 'Available', 
      render: (val) => <span className={`${styles.qtyText} ${styles.availableText}`}>{val}</span>
    },
    { key: 'min_stock_level', label: 'Min Stock' },
    { 
      key: 'status', 
      label: 'Status', 
      render: (val) => <StatusBadge status={val} />
    },
    { 
      key: 'last_updated', 
      label: 'Last Updated', 
      render: (val) => new Date(val).toLocaleString() 
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div className={styles.actions}>
          <button 
            className={styles.iconBtn} 
            title="Manual Adjustment"
            onClick={() => setAdjustingItem(row)}
          >
            <FiEdit3 />
          </button>
          <button 
            className={styles.iconBtn} 
            title="View History"
            onClick={() => navigate(`${ROUTES.INVENTORY_HISTORY}?sku=${row.product?.sku}`)}
          >
            <FiClock />
          </button>
        </div>
      )
    }
  ];

  return (
    <PageContainer 
      title="Inventory Management"
      actions={
        <>
          <Button variant="secondary" onClick={() => refetch()} isLoading={isPending}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
          </Button>
          {isBkr && (
            <Button variant="primary" onClick={() => setIsUploadModalOpen(true)}>
              <FiUploadCloud style={{ marginRight: '8px' }} /> Upload Inventory
            </Button>
          )}
        </>
      }
    >
      <Card>
        <div className={styles.toolbar}>
          <SearchBar onSearch={handleSearch} placeholder="Search SKU, Product, Warehouse..." />
          <div className={styles.filters}>
            <select className={styles.select} value={warehouseFilter} onChange={(e) => { setWarehouseFilter(e.target.value); setPage(1); }}>
              <option value="">All Warehouses</option>
              {(warehouses || []).map(wh => <option key={wh.id} value={wh.id}>{wh.name}</option>)}
            </select>
            <select className={styles.select} value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All Stock Statuses</option>
              <option value="Healthy">Healthy Stock</option>
              <option value="Low">Low Stock</option>
              <option value="Negative">Negative Stock</option>
            </select>
          </div>
        </div>

        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {isPending ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading inventory...</td></tr>
            ) : inventoryData?.length === 0 ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No inventory records found.</td></tr>
            ) : (
              inventoryData?.map((row, i) => (
                <TableRow key={`${row.product?.sku}-${row.warehouse_id}-${i}`} row={row} columns={columns} />
              ))
            )}
          </tbody>
        </DataTable>

        {totalPages > 1 && (
          <TablePagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>

      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
      />

      <AdjustmentModal 
        isOpen={!!adjustingItem} 
        onClose={() => setAdjustingItem(null)}
        inventoryRow={adjustingItem}
        onSubmit={handleAdjustmentSubmit}
        isLoading={adjustMutation.isPending}
      />
    </PageContainer>
  );
};

export default Inventory;

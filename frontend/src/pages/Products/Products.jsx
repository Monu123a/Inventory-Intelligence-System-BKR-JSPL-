import React, { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import { StatusBadge } from '../../components/StatusBadge/StatusBadge';
import Button from '../../components/forms/Button';
import { SearchBar } from '../../components/forms/SearchBar';
import { ProductFormModal } from './components/ProductFormModal';
import { ConfirmationDialog } from '../../components/Modal/ConfirmationDialog';
import { useProducts, useCreateProduct, useUpdateProduct, useBulkUpdateProducts, useProductFilters, useDeleteProduct } from '../../hooks/useProducts';
import { FiPlus, FiEdit2, FiRefreshCw, FiCheckSquare, FiXSquare, FiTrash2 } from 'react-icons/fi';
import styles from './Products.module.css';

const Products = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [brandFilter, setBrandFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  const [selectedSkus, setSelectedSkus] = useState(new Set());
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, type: null, sku: null });

  const { data: products, totalPages, isPending, refetch } = useProducts({
    search, category: categoryFilter, brand: brandFilter, status: statusFilter, page, limit: 15
  });

  const { data: filtersData } = useProductFilters();
  const categories = filtersData?.categories || [];
  const brands = filtersData?.brands || [];

  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct();
  const bulkMutation = useBulkUpdateProducts();
  const deleteMutation = useDeleteProduct();

  const handleSearch = React.useCallback((val) => { 
    setSearch(val); 
    setPage(1); 
  }, []);
  
  const handleSelectRow = (sku) => {
    const next = new Set(selectedSkus);
    if (next.has(sku)) next.delete(sku);
    else next.add(sku);
    setSelectedSkus(next);
  };
  
  const handleSelectAll = () => {
    if (selectedSkus.size === products?.length) {
      setSelectedSkus(new Set());
    } else {
      setSelectedSkus(new Set(products?.map(p => p.sku)));
    }
  };

  const handleFormSubmit = (data) => {
    if (editingProduct) {
      updateMutation.mutate({ sku: editingProduct.sku, data }, {
        onSuccess: () => setIsFormModalOpen(false)
      });
    } else {
      createMutation.mutate(data, {
        onSuccess: () => setIsFormModalOpen(false)
      });
    }
  };

  const handleBulkAction = (action) => {
    setConfirmDialog({ isOpen: true, type: `bulk_${action}` });
  };

  const executeConfirmAction = () => {
    if (confirmDialog.type === 'bulk_activate') {
      bulkMutation.mutate({ skus: Array.from(selectedSkus), data: { status: 'Active' }, products: products }, {
        onSuccess: () => { setSelectedSkus(new Set()); setConfirmDialog({ isOpen: false }); }
      });
    } else if (confirmDialog.type === 'bulk_deactivate') {
      bulkMutation.mutate({ skus: Array.from(selectedSkus), data: { status: 'Inactive' }, products: products }, {
        onSuccess: () => { setSelectedSkus(new Set()); setConfirmDialog({ isOpen: false }); }
      });
    } else if (confirmDialog.type === 'status_toggle') {
      const prod = products.find(p => p.sku === confirmDialog.sku);
      if (prod) {
        const newStatus = prod.status === 'Active' ? 'Inactive' : 'Active';
        const updatedData = { ...prod, status: newStatus };
        updateMutation.mutate({ sku: prod.sku, data: updatedData }, {
          onSuccess: () => setConfirmDialog({ isOpen: false })
        });
      }
    } else if (confirmDialog.type === 'hard_delete') {
      deleteMutation.mutate(confirmDialog.sku, {
        onSuccess: () => setConfirmDialog({ isOpen: false })
      });
    }
  };

  const columns = [
    {
      key: 'select',
      label: <input type="checkbox" onChange={handleSelectAll} checked={products?.length > 0 && selectedSkus.size === products?.length} />,
      render: (_, row) => (
        <input 
          type="checkbox" 
          checked={selectedSkus.has(row.sku)} 
          onChange={(e) => { e.stopPropagation(); handleSelectRow(row.sku); }} 
        />
      )
    },
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: 'Product Name' },
    { key: 'category', label: 'Category' },
    { key: 'brand', label: 'Brand' },
    { key: 'hsn', label: 'HSN' },
    { key: 'barcode', label: 'Barcode' },
    { key: 'min_stock_level', label: 'Min Stock' },
    { key: 'item_rate', label: 'Item Rate', render: (val) => `₹${val?.toFixed(2)}` },
    { 
      key: 'status', 
      label: 'Status', 
      render: (val) => <StatusBadge status={val} />
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div className={styles.actions}>
          <button className={styles.iconBtn} onClick={(e) => { e.stopPropagation(); setEditingProduct(row); setIsFormModalOpen(true); }} title="Edit">
            <FiEdit2 />
          </button>
          <button className={styles.iconBtn} onClick={(e) => { e.stopPropagation(); setConfirmDialog({ isOpen: true, type: 'hard_delete', sku: row.sku }); }} style={{ color: 'var(--danger)' }} title="Delete">
            <FiTrash2 />
          </button>
          <button 
            className={styles.textBtn} 
            onClick={(e) => { e.stopPropagation(); setConfirmDialog({ isOpen: true, type: 'status_toggle', sku: row.sku }); }}
          >
            {row.status === 'Active' ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      )
    }
  ];

  return (
    <PageContainer 
      title="Product Master"
      actions={
        <>
          <Button variant="secondary" onClick={() => refetch()} isLoading={isPending}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
          </Button>
          <Button variant="primary" onClick={() => { setEditingProduct(null); setIsFormModalOpen(true); }}>
            <FiPlus style={{ marginRight: '8px' }} /> Add Product
          </Button>
        </>
      }
    >
      <Card>
        <div className={styles.toolbar}>
          <SearchBar onSearch={handleSearch} placeholder="Search SKU, Name, Brand, Barcode..." />
          <div className={styles.filters}>
            <select className={styles.select} value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}>
              <option value="">All Categories</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select className={styles.select} value={brandFilter} onChange={(e) => { setBrandFilter(e.target.value); setPage(1); }}>
              <option value="">All Brands</option>
              {brands.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
            <select className={styles.select} value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All Statuses</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>
        </div>

        {selectedSkus.size > 0 && (
          <div className={styles.bulkActions}>
            <span className={styles.bulkText}>{selectedSkus.size} product(s) selected</span>
            <div className={styles.bulkBtns}>
              <Button size="sm" variant="secondary" onClick={() => handleBulkAction('activate')}>
                <FiCheckSquare style={{ marginRight: '4px' }} /> Activate
              </Button>
              <Button size="sm" variant="secondary" onClick={() => handleBulkAction('deactivate')}>
                <FiXSquare style={{ marginRight: '4px' }} /> Deactivate
              </Button>
            </div>
          </div>
        )}

        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {isPending ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading products...</td></tr>
            ) : products?.length === 0 ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No products found.</td></tr>
            ) : (
              products?.map(row => (
                <TableRow key={row.sku} row={row} columns={columns} />
              ))
            )}
          </tbody>
        </DataTable>

        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', padding: '15px' }}>
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{ padding: '5px 15px', cursor: page <= 1 ? 'not-allowed' : 'pointer' }}
            >
              Previous
            </button>
            <span style={{ alignSelf: 'center' }}>Page {page} of {totalPages}</span>
            <button 
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              style={{ padding: '5px 15px', cursor: page >= totalPages ? 'not-allowed' : 'pointer' }}
            >
              Next
            </button>
          </div>
        )}
      </Card>

      <ProductFormModal 
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        onSubmit={handleFormSubmit}
        initialData={editingProduct}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      <ConfirmationDialog 
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog({ isOpen: false, type: null, sku: null })}
        onConfirm={executeConfirmAction}
        title="Confirm Action"
        message={
          confirmDialog.type === 'bulk_activate' ? `Are you sure you want to activate ${selectedSkus.size} products?` :
          confirmDialog.type === 'bulk_deactivate' ? `Are you sure you want to deactivate ${selectedSkus.size} products?` :
          confirmDialog.type === 'hard_delete' ? `WARNING: Are you sure you want to completely delete SKU ${confirmDialog.sku}? This action cannot be undone. If it has historical inventory, the deletion will fail.` :
          `Are you sure you want to change the status of this product?`
        }
        confirmText={confirmDialog.type === 'hard_delete' ? 'Delete Permanently' : 'Confirm'}
        isLoading={bulkMutation.isPending || updateMutation.isPending || deleteMutation.isPending}
        isDanger={confirmDialog.type === 'bulk_deactivate' || confirmDialog.type === 'hard_delete'}
      />
    </PageContainer>
  );
};

export default Products;

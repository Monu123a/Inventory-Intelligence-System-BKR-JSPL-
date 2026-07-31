import React, { useState, useCallback } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import { StatusBadge } from '../../components/StatusBadge/StatusBadge';
import { SearchBar } from '../../components/forms/SearchBar';
import Button from '../../components/forms/Button';
import { ConfirmationDialog } from '../../components/Modal/ConfirmationDialog';
import { WarehouseFormModal } from './components/WarehouseFormModal';
import { WarehouseDetailsModal } from './components/WarehouseDetailsModal';
import { useWarehouses, useCreateWarehouse, useUpdateWarehouse, useDeactivateWarehouse } from '../../hooks/useWarehouses';
import { FiPlus, FiRefreshCw, FiEye, FiEdit2, FiPower } from 'react-icons/fi';
import styles from './Warehouses.module.css';

const Warehouses = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modals state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(null);
  const [selectedWarehouse, setSelectedWarehouse] = useState(null);

  const { data, totalPages, isPending, refetch } = useWarehouses({ search, statusFilter, page, limit: 10 });
  const createMutation = useCreateWarehouse();
  const updateMutation = useUpdateWarehouse();
  const deactivateMutation = useDeactivateWarehouse();

  const handleSearch = useCallback((val) => { setSearch(val); setPage(1); }, []);

  const openCreate = () => {
    setSelectedWarehouse(null);
    setIsFormOpen(true);
  };

  const openEdit = (wh) => {
    setSelectedWarehouse(wh);
    setIsFormOpen(true);
  };

  const openDetails = (wh) => {
    setSelectedWarehouse(wh);
    setIsDetailsOpen(true);
  };

  const requestDeactivate = (wh) => {
    setConfirmDeactivate(wh);
  };

  const executeDeactivate = () => {
    if (confirmDeactivate) {
      deactivateMutation.mutate(
        { id: confirmDeactivate.id, data: confirmDeactivate },
        { onSuccess: () => setConfirmDeactivate(null) }
      );
    }
  };

  const handleFormSubmit = (formData) => {
    if (selectedWarehouse) {
      updateMutation.mutate(
        { id: selectedWarehouse.id, data: formData },
        { onSuccess: () => setIsFormOpen(false) }
      );
    } else {
      createMutation.mutate(formData, { onSuccess: () => setIsFormOpen(false) });
    }
  };

  const columns = [
    { key: 'name', label: 'Warehouse Name', render: (val) => <span className={styles.nameText}>{val}</span> },
    { key: 'code', label: 'Code', render: (val) => <span className={styles.codeText}>{val}</span> },
    { key: 'address', label: 'Address', render: (val) => val || '-' },
    { key: 'contact_person', label: 'Contact Person', render: (val) => val || '-' },
    { key: 'phone_number', label: 'Phone', render: (val) => val || '-' },
    { key: 'total_products', label: 'Total Products', render: (val) => val || 0 },
    { key: 'total_inventory', label: 'Total Inventory', render: (val) => val || 0 },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div className={styles.actionsGroup}>
          <button className={styles.iconBtn} title="View Details" onClick={() => openDetails(row)}><FiEye /></button>
          <button className={styles.iconBtn} title="Edit Warehouse" onClick={() => openEdit(row)}><FiEdit2 /></button>
          <button 
            className={`${styles.iconBtn} ${row.status === 'Active' ? styles.dangerBtn : styles.successBtn}`} 
            title={row.status === 'Active' ? 'Deactivate' : 'Activate'} 
            onClick={() => requestDeactivate(row)}
          >
            <FiPower />
          </button>
        </div>
      )
    }
  ];

  const deactivateWarningMessage = confirmDeactivate?.total_inventory > 0 
    ? `WARNING: This warehouse currently holds ${confirmDeactivate.total_inventory} items in inventory. Deactivating it will hide it from operational dropdowns but will NOT erase the inventory. Are you sure you want to proceed?`
    : `Are you sure you want to change the status of ${confirmDeactivate?.name}?`;

  return (
    <PageContainer 
      title="Warehouse Management"
      actions={
        <>
          <Button variant="secondary" onClick={() => refetch()} isLoading={isPending}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
          </Button>
          <Button variant="primary" onClick={openCreate}>
            <FiPlus style={{ marginRight: '8px' }} /> Add Warehouse
          </Button>
        </>
      }
    >
      <Card>
        <div className={styles.toolbar}>
          <SearchBar onSearch={handleSearch} placeholder="Search by Name, Code, Contact, Address..." />
          <select 
            className={styles.statusFilter} 
            value={statusFilter} 
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Statuses</option>
            <option value="Active">Active Only</option>
            <option value="Inactive">Inactive Only</option>
          </select>
        </div>

        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {isPending ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading warehouses...</td></tr>
            ) : data?.length === 0 ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No warehouses found.</td></tr>
            ) : (
              data?.map((row) => (
                <TableRow key={row.id} row={row} columns={columns} />
              ))
            )}
          </tbody>
        </DataTable>

        {totalPages > 1 && (
          <TablePagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>

      <WarehouseFormModal 
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
        onSubmit={handleFormSubmit}
        initialData={selectedWarehouse}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      <WarehouseDetailsModal 
        isOpen={isDetailsOpen} 
        onClose={() => setIsDetailsOpen(false)} 
        warehouse={selectedWarehouse}
      />

      <ConfirmationDialog 
        isOpen={!!confirmDeactivate}
        onClose={() => setConfirmDeactivate(null)}
        onConfirm={executeDeactivate}
        title={`Confirm Status Change`}
        message={deactivateWarningMessage}
        confirmText="Yes, Proceed"
        isDanger={confirmDeactivate?.status === 'Active'}
        isLoading={deactivateMutation.isPending}
      />
    </PageContainer>
  );
};

export default Warehouses;

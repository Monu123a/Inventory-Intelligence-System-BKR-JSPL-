import React, { useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getWarehouses } from '../../services/warehouses';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import { HistoryFilters } from './components/HistoryFilters';
import { HistoryDetailsModal } from './components/HistoryDetailsModal';
import { useInventoryHistory, useInventoryHistoryExport } from '../../hooks/useInventoryHistory';
import { FiEye } from 'react-icons/fi';
import styles from './InventoryHistory.module.css';

const EventBadge = ({ source }) => {
  const s = source?.toLowerCase() || '';
  let colorClass = styles.badgeNeutral;
  if (s.includes('amazon')) colorClass = styles.badgeAmazon;
  else if (s.includes('upload')) colorClass = styles.badgeUpload;
  else if (s.includes('manual')) colorClass = styles.badgeManual;
  else if (s.includes('transfer in')) colorClass = styles.badgeTransferIn;
  else if (s.includes('transfer out')) colorClass = styles.badgeTransferOut;

  return <span className={`${styles.badge} ${colorClass}`}>{source}</span>;
};

const InventoryHistory = () => {
  const [searchParams] = useSearchParams();
  const initialSku = searchParams.get('sku') || '';

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [warehouseId, setWarehouseId] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [skuFilter, setSkuFilter] = useState(initialSku);

  const [selectedRecord, setSelectedRecord] = useState(null);

  const { data, allFilteredData, totalPages, isPending, refetch } = useInventoryHistory({
    search, dateRange, warehouseId, sourceFilter, skuFilter, page, limit: 15
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses'],
    queryFn: getWarehouses,
  });

  const { exportToCsv } = useInventoryHistoryExport();

  const handleSearch = useCallback((val) => { setSearch(val); setPage(1); }, []);
  
  const handleExport = () => {
    exportToCsv(allFilteredData);
  };

  const columns = [
    { 
      key: 'timestamp', 
      label: 'Date/Time', 
      render: (val) => new Date(val).toLocaleString() 
    },
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product Name' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { 
      key: 'source', 
      label: 'Event Type',
      render: (val) => <EventBadge source={val} />
    },
    { key: 'qty_before', label: 'Qty Before', render: (val) => <span className={styles.qtyText}>{val}</span> },
    { 
      key: 'qty_changed', 
      label: 'Change',
      render: (val) => (
        <span className={`${styles.qtyChange} ${val > 0 ? styles.pos : val < 0 ? styles.neg : ''}`}>
          {val > 0 ? '+' : ''}{val}
        </span>
      )
    },
    { key: 'qty_after', label: 'Qty After', render: (val) => <span className={styles.qtyText}>{val}</span> },
    { key: 'reference_id', label: 'Ref ID' },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <button 
          className={styles.viewBtn} 
          onClick={() => setSelectedRecord(row)}
          title="View Details"
        >
          <FiEye /> View
        </button>
      )
    }
  ];

  return (
    <PageContainer title="Inventory History">
      <Card>
        <HistoryFilters 
          search={search} setSearch={handleSearch}
          dateRange={dateRange} setDateRange={setDateRange}
          warehouseId={warehouseId} setWarehouseId={setWarehouseId}
          warehouses={warehouses}
          sourceFilter={sourceFilter} setSourceFilter={setSourceFilter}
          skuFilter={skuFilter} setSkuFilter={setSkuFilter}
          onRefresh={refetch} isPending={isPending}
          onExport={handleExport} disableExport={!allFilteredData || allFilteredData.length === 0}
        />

        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {isPending ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading history...</td></tr>
            ) : data?.length === 0 ? (
              <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No history records found.</td></tr>
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

      <HistoryDetailsModal 
        isOpen={!!selectedRecord}
        onClose={() => setSelectedRecord(null)}
        record={selectedRecord}
      />
    </PageContainer>
  );
};

export default InventoryHistory;

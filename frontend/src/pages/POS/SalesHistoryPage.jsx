import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { posService } from '../../services/pos';
import { handleApiError } from '../../utils/errorHandler';
import { DataTable, TableHeader, TableRow, TablePagination } from '../../components/DataTable';
import Button from '../../components/forms/Button';
import styles from './SalesHistoryPage.module.css';
import { FiEye, FiRefreshCw, FiCheck, FiX, FiClock } from 'react-icons/fi';

const SalesHistoryPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // Filters
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [invoiceType, setInvoiceType] = useState('');
  const [returnStatus, setReturnStatus] = useState('');
  const [tallyStatus, setTallyStatus] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  const [skip, setSkip] = useState(0);
  const limit = 20;

  const [retryingId, setRetryingId] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['sales', skip, limit, search, status, invoiceType, returnStatus, tallyStatus, startDate, endDate],
    queryFn: () => posService.getSalesHistory({
      skip, limit,
      search: search || undefined,
      status: status || undefined,
      invoice_type: invoiceType || undefined,
      return_status: returnStatus || undefined,
      tally_status: tallyStatus || undefined,
      date_from: startDate || undefined,
      date_to: endDate || undefined,
    }),
  });

  const sales = data?.items || [];
  const total = data?.total || 0;

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString();
  };

  const retryTallyMutation = useMutation({
    mutationFn: posService.retryTallySync,
    onMutate: (saleId) => setRetryingId(saleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales'] });
    },
    onError: (err) => {
      handleApiError(err, "Failed to retry Tally sync");
    },
    onSettled: () => setRetryingId(null)
  });

  const handleRetryTally = (saleId) => {
    retryTallyMutation.mutate(saleId);
  };

  const renderTallyStatus = (sale) => {
    if (sale.invoice_type !== 'B2B') return <span className={styles.tallyBadgeNA}>N/A</span>;
    
    switch (sale.tally_sync_status) {
      case 'SUCCESS':
        return <span className={`${styles.tallyBadge} ${styles.tallySuccess}`} title={sale.tally_reference}><FiCheck /> Success</span>;
      case 'FAILED':
        return <span className={`${styles.tallyBadge} ${styles.tallyFailed}`} title={sale.tally_error_message}><FiX /> Failed</span>;
      case 'PENDING':
        return <span className={`${styles.tallyBadge} ${styles.tallyPending}`}><FiClock /> Pending</span>;
      default:
        return <span className={styles.tallyBadgeNA}>{sale.tally_sync_status}</span>;
    }
  };

  const renderReturnStatus = (status) => {
    if (status === 'Fully Returned') {
      return <span className={`${styles.returnBadge} ${styles.returnFull}`}>Fully Returned</span>;
    }
    if (status === 'Partially Returned') {
      return <span className={`${styles.returnBadge} ${styles.returnPartial}`}>Partially Returned</span>;
    }
    return <span className={`${styles.returnBadge} ${styles.returnNone}`}>None</span>;
  };

  const columns = [
    { key: 'sale_date', label: 'Date', render: (val) => formatDate(val) },
    { 
      key: 'bill_number', 
      label: 'Bill / Invoice No.', 
      render: (_, sale) => (
        <>
          <div className={styles.billNumber}>{sale.bill_number}</div>
          {sale.invoice_number && <div className={styles.invoiceNumber}>{sale.invoice_number}</div>}
        </>
      )
    },
    { key: 'invoice_type', label: 'Type', render: (val) => <span className={styles.typeBadge}>{val || 'B2C'}</span> },
    {
      key: 'customer',
      label: 'Customer',
      render: (_, sale) => (
        <>
          <div className={styles.customerName}>{sale.customer_name || 'Walk-in'}</div>
          {sale.customer_gstin && <div className={styles.customerGstin}>{sale.customer_gstin}</div>}
        </>
      )
    },
    { key: 'grand_total', label: 'Total (₹)', render: (val) => <span style={{fontWeight: '600'}}>₹{val.toFixed(2)}</span> },
    {
      key: 'quantities',
      label: 'Sold/Ret/Net Qty',
      render: (_, sale) => (
        <div style={{ fontSize: '13px' }}>
          <span title="Total Sold">{sale.total_sold || 0}</span> / <span title="Total Returned" style={{ color: sale.returned_quantity > 0 ? '#c2410c' : 'inherit' }}>{sale.returned_quantity || 0}</span> / <span title="Net Quantity" style={{ fontWeight: 'bold' }}>{sale.remaining_quantity || 0}</span>
        </div>
      )
    },
    { key: 'return_status', label: 'Return Status', render: (val) => renderReturnStatus(val) },
    { key: 'tally_sync_status', label: 'Tally Sync', render: (_, sale) => renderTallyStatus(sale) },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, sale) => (
        <div className={styles.actionsCell}>
          <button 
            className={styles.actionBtn} 
            title="View Invoice"
            onClick={() => navigate(`/sales/${sale.id}/invoice`)}
          >
            <FiEye /> View
          </button>
          {sale.linked_sales_return_ids?.length > 0 && (
            <button 
              className={styles.actionBtn} 
              title="View Returns"
              onClick={() => navigate(`/sales-returns/${sale.linked_sales_return_ids[0]}`)}
            >
              <FiRefreshCw /> Returns
            </button>
          )}
          {sale.invoice_type === 'B2B' && (sale.tally_sync_status === 'FAILED' || sale.tally_sync_status === 'PENDING') && (
            <button 
              className={`${styles.actionBtn} ${styles.retryBtn}`} 
              title="Retry Tally Sync"
              onClick={() => handleRetryTally(sale.id)}
              disabled={retryingId === sale.id}
            >
              <FiRefreshCw className={retryingId === sale.id ? styles.spinning : ''} /> Retry
            </button>
          )}
        </div>
      )
    }
  ];

  return (
    <div className={styles.historyContainer}>
      <div className={styles.header}>
        <h1>Sales History</h1>
      </div>

      <div className={styles.filtersWrapper}>
        <div className={styles.filtersRow}>
          <input 
            className={styles.searchInput}
            placeholder="Search Bill No, Invoice No, or Customer..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSkip(0);
            }}
            autoFocus
          />
          <div className={styles.dateFilters}>
            <input 
              type="date"
              className={styles.dateInput}
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setSkip(0); }}
              title="Start Date"
            />
            <span className={styles.dateSeparator}>to</span>
            <input 
              type="date"
              className={styles.dateInput}
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setSkip(0); }}
              title="End Date"
            />
          </div>
        </div>
        <div className={styles.filtersRow}>
          <select 
            className={styles.filterSelect}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setSkip(0);
            }}
          >
            <option value="">All Sale Statuses</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          <select 
            className={styles.filterSelect}
            value={invoiceType}
            onChange={(e) => {
              setInvoiceType(e.target.value);
              setSkip(0);
            }}
          >
            <option value="">All Invoice Types</option>
            <option value="B2C">B2C</option>
            <option value="B2B">B2B</option>
          </select>
          <select 
            className={styles.filterSelect}
            value={returnStatus}
            onChange={(e) => {
              setReturnStatus(e.target.value);
              setSkip(0);
            }}
          >
            <option value="">All Return Statuses</option>
            <option value="Active Sales">Active Sales</option>
            <option value="None">None</option>
            <option value="Partially Returned">Partially Returned</option>
            <option value="Fully Returned">Fully Returned</option>
          </select>
          <select 
            className={styles.filterSelect}
            value={tallyStatus}
            onChange={(e) => {
              setTallyStatus(e.target.value);
              setSkip(0);
            }}
          >
            <option value="">All Tally Statuses</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">Pending</option>
            <option value="NOT_APPLICABLE">Not Applicable</option>
          </select>
          
          <button className={styles.clearBtn} onClick={() => {
            setSearch(''); setStatus(''); setInvoiceType(''); setReturnStatus(''); setTallyStatus(''); setStartDate(''); setEndDate(''); setSkip(0);
          }}>Clear Filters</button>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} style={{textAlign: 'center', padding: '2rem'}}>Loading...</td>
              </tr>
            ) : sales.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{textAlign: 'center', padding: '2rem'}}>No sales found matching your filters.</td>
              </tr>
            ) : (
              sales.map((sale) => (
                <TableRow key={sale.id} row={sale} columns={columns} />
              ))
            )}
          </tbody>
        </DataTable>
        
        {total > limit && (
          <TablePagination 
            currentPage={Math.floor(skip / limit) + 1} 
            totalPages={Math.ceil(total / limit)} 
            onPageChange={(p) => setSkip((p - 1) * limit)} 
          />
        )}
      </div>
    </div>
  );
};

export default SalesHistoryPage;

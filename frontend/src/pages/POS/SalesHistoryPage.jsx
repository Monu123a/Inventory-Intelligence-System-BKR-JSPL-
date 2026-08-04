import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import styles from './SalesHistoryPage.module.css';
import { FiEye, FiRefreshCw, FiCheck, FiX, FiClock } from 'react-icons/fi';

const SalesHistoryPage = () => {
  const navigate = useNavigate();
  const [sales, setSales] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  
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

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const params = { skip, limit };
      if (search) params.search = search;
      if (status) params.status = status;
      if (invoiceType) params.invoice_type = invoiceType;
      if (returnStatus) params.return_status = returnStatus;
      if (tallyStatus) params.tally_status = tallyStatus;
      if (startDate) params.date_from = startDate;
      if (endDate) params.date_to = endDate;
      
      const res = await api.get('/api/pos/history', { params });
      setSales(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setLoading(false);
    }
  }, [limit, search, skip, status, invoiceType, returnStatus, tallyStatus, startDate, endDate]);

  // Debounced fetch
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHistory();
    }, 500);
    return () => clearTimeout(timer);
  }, [fetchHistory]);

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString();
  };

  const handleRetryTally = async (saleId) => {
    setRetryingId(saleId);
    try {
      await api.post(`/api/pos/sales/${saleId}/retry-tally`);
      fetchHistory(); // refresh data
    } catch (err) {
      console.error("Failed to retry Tally sync", err);
      alert("Failed to retry Tally sync: " + (err.response?.data?.detail || err.message));
    } finally {
      setRetryingId(null);
    }
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
        <table className={styles.historyTable}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Bill / Invoice No.</th>
              <th>Type</th>
              <th>Customer</th>
              <th>Total (₹)</th>
              <th>Sold/Ret/Net Qty</th>
              <th>Return Status</th>
              <th>Tally Sync</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" style={{textAlign: 'center'}}>Loading...</td>
              </tr>
            ) : sales.length === 0 ? (
              <tr>
                <td colSpan="7" style={{textAlign: 'center'}}>No sales found matching your filters.</td>
              </tr>
            ) : (
              sales.map((sale) => (
                <tr key={sale.id}>
                  <td>{formatDate(sale.sale_date)}</td>
                  <td>
                    <div className={styles.billNumber}>{sale.bill_number}</div>
                    {sale.invoice_number && <div className={styles.invoiceNumber}>{sale.invoice_number}</div>}
                  </td>
                  <td>
                    <span className={styles.typeBadge}>{sale.invoice_type || 'B2C'}</span>
                  </td>
                  <td>
                    <div className={styles.customerName}>{sale.customer_name || 'Walk-in'}</div>
                    {sale.customer_gstin && <div className={styles.customerGstin}>{sale.customer_gstin}</div>}
                  </td>
                  <td style={{fontWeight: '600'}}>₹{sale.grand_total.toFixed(2)}</td>
                  <td>
                    <div style={{ fontSize: '13px' }}>
                      <span title="Total Sold">{sale.total_sold || 0}</span> / <span title="Total Returned" style={{ color: sale.returned_quantity > 0 ? '#c2410c' : 'inherit' }}>{sale.returned_quantity || 0}</span> / <span title="Net Quantity" style={{ fontWeight: 'bold' }}>{sale.remaining_quantity || 0}</span>
                    </div>
                  </td>
                  <td>{renderReturnStatus(sale.return_status)}</td>
                  <td>
                    {renderTallyStatus(sale)}
                  </td>
                  <td className={styles.actionsCell}>
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
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        
        <div className={styles.pagination}>
          <span>Showing {Math.min(skip + 1, total)} - {Math.min(skip + sales.length, total)} of {total}</span>
          <div className={styles.pageBtns}>
            <button 
              className={styles.pageBtn}
              disabled={skip === 0}
              onClick={() => setSkip(skip - limit)}
            >
              Previous
            </button>
            <button 
              className={styles.pageBtn}
              disabled={skip + limit >= total}
              onClick={() => setSkip(skip + limit)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SalesHistoryPage;

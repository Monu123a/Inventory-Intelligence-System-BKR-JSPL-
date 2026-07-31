import React, { useState, useEffect, useCallback } from 'react';
import api from '../../services/api';
import styles from './SalesHistoryPage.module.css';

const SalesHistoryPage = () => {
  const [sales, setSales] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [skip, setSkip] = useState(0);
  const limit = 20;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const params = { skip, limit };
      if (search) params.search = search;
      if (status) params.status = status;
      
      const res = await api.get('/api/pos/history', { params });
      setSales(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setLoading(false);
    }
  }, [limit, search, skip, status]);

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

  return (
    <div className={styles.historyContainer}>
      <div className={styles.header}>
        <h1>Offline Sales History</h1>
      </div>

      <div className={styles.filters}>
        <input 
          className={styles.searchInput}
          placeholder="Search by Bill No or Customer..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setSkip(0);
          }}
        />
        <select 
          className={styles.statusSelect}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setSkip(0);
          }}
        >
          <option value="">All Statuses</option>
          <option value="Completed">Completed</option>
          <option value="Cancelled">Cancelled</option>
        </select>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.historyTable}>
          <thead>
            <tr>
              <th>Bill Number</th>
              <th>Date</th>
              <th>Customer</th>
              <th>Items</th>
              <th>Total</th>
              <th>Method</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" style={{textAlign: 'center'}}>Loading...</td>
              </tr>
            ) : sales.length === 0 ? (
              <tr>
                <td colSpan="7" style={{textAlign: 'center'}}>No sales found.</td>
              </tr>
            ) : (
              sales.map((sale) => (
                <tr key={sale.id}>
                  <td style={{fontWeight: '500'}}>{sale.bill_number}</td>
                  <td>{formatDate(sale.sale_date)}</td>
                  <td>{sale.customer_name || 'Walk-in'}</td>
                  <td>{sale.items_count}</td>
                  <td style={{fontWeight: '600'}}>₹{sale.grand_total.toFixed(2)}</td>
                  <td>
                    <span className={styles.paymentBadge}>{sale.payment_method}</span>
                  </td>
                  <td>
                    <span className={`${styles.statusBadge} ${styles[sale.status.toLowerCase()] || ''}`}>
                      {sale.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        
        <div className={styles.pagination}>
          <span>Showing {sales.length} of {total}</span>
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

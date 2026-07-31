import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import styles from './TransferList.module.css';

const TransferList = () => {
  const navigate = useNavigate();
  const [transfers, setTransfers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock API call
    setTimeout(() => {
      setTransfers([
        { id: 'TRF-001', from: 'Main Warehouse', to: 'Store A', status: 'Draft', createdDate: '2023-10-01', dispatchDate: '-', value: 1200 },
        { id: 'TRF-002', from: 'Main Warehouse', to: 'Store B', status: 'Pending Approval', createdDate: '2023-10-02', dispatchDate: '-', value: 3400 },
        { id: 'TRF-003', from: 'Supplier C', to: 'Main Warehouse', status: 'Approved', createdDate: '2023-10-03', dispatchDate: '-', value: 5000 },
        { id: 'TRF-004', from: 'Main Warehouse', to: 'Store D', status: 'Dispatched', createdDate: '2023-10-04', dispatchDate: '2023-10-05', value: 2500 },
        { id: 'TRF-005', from: 'Main Warehouse', to: 'Store E', status: 'Completed', createdDate: '2023-09-28', dispatchDate: '2023-09-29', value: 4100 },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const getStatusBadge = (status) => {
    const statusClass = status.replace(/\s+/g, '').toLowerCase();
    return <span className={`${styles.badge} ${styles[statusClass] || styles.defaultBadge}`}>{status}</span>;
  };

  if (loading) return <div className={styles.loading}>Loading Transfers...</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <button className={styles.backBtn} onClick={() => navigate(ROUTES.REPLENISHMENT_DASHBOARD)}>&larr; Dashboard</button>
          <h1>Stock Transfers</h1>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Transfer Number</th>
              <th>From</th>
              <th>To</th>
              <th>Status</th>
              <th>Created Date</th>
              <th>Dispatch Date</th>
              <th>Value</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transfers.map((trf) => (
              <tr key={trf.id}>
                <td>{trf.id}</td>
                <td>{trf.from}</td>
                <td>{trf.to}</td>
                <td>{getStatusBadge(trf.status)}</td>
                <td>{trf.createdDate}</td>
                <td>{trf.dispatchDate}</td>
                <td>₹{trf.value.toFixed(2)}</td>
                <td>
                  <button 
                    className={styles.linkBtn} 
                    onClick={() => navigate(ROUTES.REPLENISHMENT_TRANSFER_DETAIL.replace(':transferId', trf.id))}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {transfers.length === 0 && (
          <p className={styles.emptyState}>No stock transfers found.</p>
        )}
      </div>
    </div>
  );
};

export default TransferList;

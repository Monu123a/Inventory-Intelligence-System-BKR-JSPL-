import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import styles from './TransferList.module.css'; // Re-use existing table styles

const BKRRequirementsView = () => {
  const navigate = useNavigate();
  const [transfers, setTransfers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real scenario, this would fetch from /api/transfers?status=Pending
    setTimeout(() => {
      setTransfers([
        { id: 'TRF-101', status: 'Pending', createdDate: '2023-10-15', requestedBy: 'JSPL', itemsCount: 3 },
        { id: 'TRF-102', status: 'Pending', createdDate: '2023-10-16', requestedBy: 'JSPL', itemsCount: 1 },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  if (loading) return <div className={styles.loading}>Loading JSPL Requirements...</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <h1>JSPL Replenishment Requirements</h1>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Requested By</th>
              <th>Date</th>
              <th>Items</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {transfers.map(trf => (
              <tr key={trf.id}>
                <td>{trf.id}</td>
                <td>{trf.requestedBy}</td>
                <td>{trf.createdDate}</td>
                <td>{trf.itemsCount}</td>
                <td>
                  <span className={`${styles.badge} ${styles.pending}`}>{trf.status}</span>
                </td>
                <td>
                  <button 
                    className={styles.linkBtn} 
                    onClick={() => navigate(ROUTES.REPLENISHMENT_BKR_INVOICE.replace(':id', trf.id))}
                  >
                    Process & Generate Bill
                  </button>
                </td>
              </tr>
            ))}
            {transfers.length === 0 && (
              <tr>
                <td colSpan="6" className={styles.emptyState}>No pending requirements.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BKRRequirementsView;

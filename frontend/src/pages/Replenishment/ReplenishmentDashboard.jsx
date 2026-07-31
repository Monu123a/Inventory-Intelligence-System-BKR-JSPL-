import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import styles from './ReplenishmentDashboard.module.css';

const ReplenishmentDashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ productsNeedingReplenishment: 0, estimatedValue: 0 });
  const [scheduler, setScheduler] = useState({ lastRun: null, nextRun: null });
  const [pendingTransfers, setPendingTransfers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock API call
    setTimeout(() => {
      setStats({
        productsNeedingReplenishment: 24,
        estimatedValue: 15200.50
      });
      setScheduler({
        lastRun: new Date(Date.now() - 3600000).toISOString(),
        nextRun: new Date(Date.now() + 3600000).toISOString()
      });
      setPendingTransfers([
        { id: 'TRF-001', from: 'Main Warehouse', to: 'Store A', items: 5, value: 1200 },
        { id: 'TRF-002', from: 'Main Warehouse', to: 'Store B', items: 12, value: 3400 }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  if (loading) return <div className={styles.loading}>Loading Dashboard...</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Replenishment Dashboard</h1>
        <div className={styles.actions}>
          <button className={styles.primaryBtn} onClick={() => navigate(ROUTES.REPLENISHMENT_RECOMMENDATIONS)}>
            View Recommendations
          </button>
          <button className={styles.secondaryBtn} onClick={() => navigate(ROUTES.REPLENISHMENT_TRANSFERS)}>
            All Transfers
          </button>
        </div>
      </div>

      <div className={styles.kpiCards}>
        <div className={styles.card}>
          <h3>Products Needing Replenishment</h3>
          <p className={styles.kpiValue}>{stats.productsNeedingReplenishment}</p>
        </div>
        <div className={styles.card}>
          <h3>Estimated Transfer Value</h3>
          <p className={styles.kpiValue}>₹{stats.estimatedValue.toFixed(2)}</p>
        </div>
        <div className={styles.card}>
          <h3>Scheduler Status</h3>
          <p className={styles.kpiText}>Last Run: {new Date(scheduler.lastRun).toLocaleString()}</p>
          <p className={styles.kpiText}>Next Run: {new Date(scheduler.nextRun).toLocaleString()}</p>
        </div>
      </div>

      <div className={styles.widget}>
        <h2>Pending Transfers</h2>
        {pendingTransfers.length === 0 ? (
          <p>No pending transfers.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Transfer ID</th>
                <th>From</th>
                <th>To</th>
                <th>Items</th>
                <th>Value</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {pendingTransfers.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{t.from}</td>
                  <td>{t.to}</td>
                  <td>{t.items}</td>
                  <td>₹{t.value.toFixed(2)}</td>
                  <td>
                    <button className={styles.linkBtn} onClick={() => navigate(ROUTES.REPLENISHMENT_TRANSFER_DETAIL.replace(':transferId', t.id))}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default ReplenishmentDashboard;

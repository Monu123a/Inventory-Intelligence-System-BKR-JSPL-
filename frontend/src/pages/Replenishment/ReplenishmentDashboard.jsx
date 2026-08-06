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

  // Filters State
  const [selectedHub, setSelectedHub] = useState('');
  const [selectedWarehouse, setSelectedWarehouse] = useState('');

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
        { id: 'TRF-001', from: 'Main Warehouse', to: 'Store A', items: 5, value: 1200, hub: 'Hub 1', warehouse: 'Store A' },
        { id: 'TRF-002', from: 'Main Warehouse', to: 'Store B', items: 12, value: 3400, hub: 'Hub 2', warehouse: 'Store B' }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const filteredTransfers = pendingTransfers.filter(t => {
    const matchesHub = selectedHub ? t.hub === selectedHub : true;
    const matchesWarehouse = selectedWarehouse ? t.warehouse === selectedWarehouse : true;
    return matchesHub && matchesWarehouse;
  });

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
          <button className={styles.primaryBtn} style={{ marginLeft: '10px' }} onClick={() => navigate(`${ROUTES.LOGISTICS_BATCH_DISPATCH}?source=CENTRAL`)}>
            Create Internal Distribution
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2>Pending Transfers</h2>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <select 
              value={selectedHub} 
              onChange={(e) => { setSelectedHub(e.target.value); setSelectedWarehouse(''); }}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="">All State Hubs</option>
              <option value="Hub 1">Hub 1</option>
              <option value="Hub 2">Hub 2</option>
            </select>
            <select 
              value={selectedWarehouse} 
              onChange={(e) => setSelectedWarehouse(e.target.value)}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="">All Warehouses / FCs</option>
              <option value="Store A">Store A</option>
              <option value="Store B">Store B</option>
            </select>
          </div>
        </div>
        
        {filteredTransfers.length === 0 ? (
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
              {filteredTransfers.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{t.from}</td>
                  <td>{t.to}</td>
                  <td>{t.items}</td>
                  <td>₹{t.value.toFixed(2)}</td>
                  <td>
                    <button className={styles.linkBtn} onClick={() => navigate(ROUTES.REPLENISHMENT_TRANSFER_DETAIL?.replace(':transferId', t.id) || '#')}>
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

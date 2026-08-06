import React, { useState, useEffect } from 'react';
import { useNotificationStore } from '../../stores/notificationStore';
import styles from './JSPLReplenishmentView.module.css';
import api from '../../services/api';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';

const JSPLReplenishmentView = () => {
  const navigate = useNavigate();
  const addNotification = useNotificationStore(state => state.addNotification);
  const [recommendations, setRecommendations] = useState([]);
  const [activeTransfers, setActiveTransfers] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch real recommendations data
        const recRes = await api.get('/api/replenishment/recommendations');
        setRecommendations(recRes.data);

        // Fetch active transfers
        const transfersRes = await api.get('/api/transfers?status=active');
        setActiveTransfers(transfersRes.data);
      } catch (error) {
        addNotification({ type: 'error', title: 'Error', message: 'Failed to load replenishment data' });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSelect = (id) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedItems(newSelected);
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedItems(new Set(recommendations.map(r => r.id)));
    } else {
      setSelectedItems(new Set());
    }
  };

  const handleApprove = async () => {
    if (selectedItems.size === 0) return;
    setLoading(true);
    try {
      const itemsToApprove = recommendations
        .filter(r => selectedItems.has(r.id))
        .map(r => ({ product_id: r.id, requested_qty: r.requiredQty, sku: r.sku }));

      // JSPL (1) is requesting goods FROM BKR (2) TO JSPL (1)
      const payload = {
        from_company_id: 2, 
        to_company_id: 1,
        items: itemsToApprove.map(i => ({ product_id: i.product_id, requested_qty: i.requested_qty }))
      };

      const response = await api.post('/api/transfers/create', payload);

      if (response.status !== 200 && response.status !== 201) throw new Error('Failed to create transfer');

      addNotification({ type: 'success', title: 'Success', message: 'Replenishment request sent to BKR successfully' });
      
      const newTransfer = {
        items: itemsToApprove.map(i => ({ sku: i.sku, requested_qty: i.requested_qty })),
        status: 'Pending'
      };
      setActiveTransfers([...activeTransfers, newTransfer]);
      setSelectedItems(new Set());
      
      // Refetch recommendations
      const recRes = await api.get('/api/replenishment/recommendations');
      setRecommendations(recRes.data);
    } catch (error) {
      addNotification({ type: 'error', title: 'Error', message: error.message || 'Failed to approve replenishment' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Need Replenishment</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            className={styles.approveBtn} 
            onClick={() => navigate(`${ROUTES.LOGISTICS_BATCH_DISPATCH}?source=CENTRAL`)}
          >
            Create Internal Distribution
          </button>
          <button 
            className={styles.approveBtn} 
            onClick={handleApprove}
            disabled={selectedItems.size === 0 || loading}
          >
            {loading ? 'Processing...' : `Approve Replenishment (${selectedItems.size})`}
          </button>
        </div>
      </div>

      <div className={styles.card}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>
                <input 
                  type="checkbox" 
                  className={styles.checkbox}
                  checked={selectedItems.size === recommendations.length && recommendations.length > 0}
                  onChange={handleSelectAll}
                />
              </th>
              <th>SKU</th>
              <th>Product</th>
              <th>Current Stock</th>
              <th>Required Qty</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map(item => {
              const activeTransfer = activeTransfers.find(t => t.items.some(i => i.sku === item.sku));
              const isPending = !!activeTransfer;
              return (
              <tr key={item.id}>
                <td>
                  <input 
                    type="checkbox" 
                    className={styles.checkbox}
                    checked={selectedItems.has(item.id)}
                    onChange={() => handleSelect(item.id)}
                    disabled={isPending}
                  />
                </td>
                <td>{item.sku}</td>
                <td>{item.product}</td>
                <td>{item.currentStock}</td>
                <td>{item.requiredQty}</td>
                <td>
                  {isPending ? (
                    <span className={styles.badge}>{activeTransfer.status}</span>
                  ) : (
                    <span style={{ color: '#888' }}>-</span>
                  )}
                </td>
              </tr>
            )})}
            {recommendations.length === 0 && (
              <tr>
                <td colSpan="6" style={{textAlign: 'center'}}>No items need replenishment right now.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default JSPLReplenishmentView;

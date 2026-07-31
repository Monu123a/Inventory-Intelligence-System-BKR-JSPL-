import React, { useState, useEffect } from 'react';
import { useUIStore } from '../../stores/uiStore';
import styles from './JSPLReplenishmentView.module.css';

const JSPLReplenishmentView = () => {
  const addNotification = useUIStore(state => state.addNotification);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Mocking recommendations data
    setRecommendations([
      { id: 'REC-1', sku: 'SKU-001', product: 'Widget A', requiredQty: 50, currentStock: 10 },
      { id: 'REC-2', sku: 'SKU-002', product: 'Widget B', requiredQty: 200, currentStock: 5 },
      { id: 'REC-3', sku: 'SKU-003', product: 'Widget C', requiredQty: 100, currentStock: 0 },
    ]);
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
        .map(r => ({ sku: r.sku, quantity: r.requiredQty }));

      const response = await fetch('/api/transfers/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: itemsToApprove })
      });

      if (!response.ok) throw new Error('Failed to create transfer');

      addNotification('Replenishment request sent to BKR successfully', 'success');
      
      // Remove approved items from list
      setRecommendations(recommendations.filter(r => !selectedItems.has(r.id)));
      setSelectedItems(new Set());
    } catch (error) {
      addNotification(error.message || 'Failed to approve replenishment', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Need Replenishment</h1>
        <button 
          className={styles.approveBtn} 
          onClick={handleApprove}
          disabled={selectedItems.size === 0 || loading}
        >
          {loading ? 'Processing...' : `Approve Replenishment (${selectedItems.size})`}
        </button>
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
            </tr>
          </thead>
          <tbody>
            {recommendations.map(item => (
              <tr key={item.id}>
                <td>
                  <input 
                    type="checkbox" 
                    className={styles.checkbox}
                    checked={selectedItems.has(item.id)}
                    onChange={() => handleSelect(item.id)}
                  />
                </td>
                <td>{item.sku}</td>
                <td>{item.product}</td>
                <td>{item.currentStock}</td>
                <td>{item.requiredQty}</td>
              </tr>
            ))}
            {recommendations.length === 0 && (
              <tr>
                <td colSpan="5" style={{textAlign: 'center'}}>No items need replenishment right now.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default JSPLReplenishmentView;

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import styles from './RecommendationsView.module.css';

const RecommendationsView = () => {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock API call
    setTimeout(() => {
      setRecommendations([
        { id: 1, sku: 'SKU-001', name: 'Widget A', currentStock: 50, reserved: 10, available: 40, todayDemand: 20, safetyStock: 30, suggestedQty: 10 },
        { id: 2, sku: 'SKU-002', name: 'Widget B', currentStock: 20, reserved: 5, available: 15, todayDemand: 10, safetyStock: 15, suggestedQty: 10 },
        { id: 3, sku: 'SKU-003', name: 'Super Widget', currentStock: 100, reserved: 80, available: 20, todayDemand: 15, safetyStock: 25, suggestedQty: 20 },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const handleQtyChange = (id, newQty) => {
    setRecommendations(recommendations.map(r => r.id === id ? { ...r, suggestedQty: Number(newQty) } : r));
  };

  const handleApprove = () => {
    // Mock approval
    alert('Request sent to BKR successfully!');
    navigate(ROUTES.REPLENISHMENT_TRANSFERS);
  };

  if (loading) return <div className={styles.loading}>Loading Recommendations...</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <button className={styles.backBtn} onClick={() => navigate(-1)}>&larr; Back</button>
          <h1>Replenishment Recommendations</h1>
        </div>
        <button className={styles.primaryBtn} onClick={handleApprove}>Send Request to BKR</button>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Product Name</th>
              <th>Current Stock</th>
              <th>Reserved</th>
              <th>Available</th>
              <th>Today's Demand</th>
              <th>Safety Stock</th>
              <th>Suggested Qty</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map((rec) => (
              <tr key={rec.id}>
                <td>{rec.sku}</td>
                <td>{rec.name}</td>
                <td>{rec.currentStock}</td>
                <td>{rec.reserved}</td>
                <td>{rec.available}</td>
                <td>{rec.todayDemand}</td>
                <td>{rec.safetyStock}</td>
                <td>
                  <input 
                    type="number" 
                    className={styles.qtyInput} 
                    value={rec.suggestedQty} 
                    onChange={(e) => handleQtyChange(rec.id, e.target.value)}
                    min="0"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {recommendations.length === 0 && (
          <p className={styles.emptyState}>No recommendations available at this time.</p>
        )}
      </div>
    </div>
  );
};

export default RecommendationsView;

import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import styles from './Warehouse.module.css';
import api from '../../services/api';

const WarehouseDashboard = () => {
  const [metrics, setMetrics] = useState({ totalProducts: 0, inventoryValue: 0, lowStock: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchInventory = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/warehouse-inventory');
        if (response.data) {
          const data = response.data;
          setMetrics({
            totalProducts: data.length || 0,
            inventoryValue: data.reduce((acc, item) => acc + (item.price || 0) * (item.quantity || 0), 0),
            lowStock: data.filter(item => item.quantity < 10).length || 0
          });
        }
      } catch (err) {
        console.error('Failed to load inventory for dashboard metrics', err);
      } finally {
        setLoading(false);
      }
    };
    fetchInventory();
  }, []);

  return (
    <PageContainer title="Warehouse Dashboard">
      {loading ? (
        <p>Loading metrics...</p>
      ) : (
        <div className={styles.grid}>
          <Card>
            <h3 style={{ color: '#6b7280', fontSize: '0.875rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Total Products</h3>
            <p className={styles.metric}>{metrics.totalProducts}</p>
          </Card>
          <Card>
            <h3 style={{ color: '#6b7280', fontSize: '0.875rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Inventory Value</h3>
            <p className={styles.metric}>₹{metrics.inventoryValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          </Card>
          <Card>
            <h3 style={{ color: '#6b7280', fontSize: '0.875rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Low Stock Items</h3>
            <p className={styles.metric}>{metrics.lowStock}</p>
          </Card>
        </div>
      )}
    </PageContainer>
  );
};

export default WarehouseDashboard;

import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import api from '../../services/api';
import styles from './Amazon.module.css'; // or any existing css

const AmazonLiveInventory = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await api.get('/amazon/live-inventory');
      setData(res);
    } catch (err) {
      setError('Failed to load Amazon live inventory');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { key: 'sku', label: 'SKU' },
    { key: 'network', label: 'Network (MFN/AFN)' },
    { key: 'allocated_qty', label: 'Total Allocated' },
    { key: 'reconciled_qty', label: 'Reconciled' },
    { key: 'pending_qty', label: 'Soft Reserved (Pending)' },
    { key: 'active_orders', label: 'Active Orders' },
  ];

  return (
    <PageContainer title="Amazon Live Inventory (Soft Allocation)">
      <Card noPadding>
        <div style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb', backgroundColor: '#f9fafb' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', color: '#374151' }}>Real-time SP-API Sync</h3>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: '#6b7280' }}>
            Orders shown here are "soft allocated" to prevent overselling. Standard inventory is only permanently deducted when the Amazon Settlement Report reconciles the shipped items.
          </p>
        </div>
        
        <div style={{ padding: '1rem' }}>
          <button 
            onClick={fetchData}
            style={{ padding: '0.5rem 1rem', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer' }}
          >
            Refresh Dashboard
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Syncing with SP-API...</td></tr>
              ) : error ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem', color: 'red' }}>{error}</td></tr>
              ) : data.length === 0 ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No active soft allocations found.</td></tr>
              ) : (
                data.map((row, idx) => (
                  <TableRow key={idx} row={row} columns={columns} />
                ))
              )}
            </tbody>
          </DataTable>
        </div>
      </Card>
    </PageContainer>
  );
};

export default AmazonLiveInventory;

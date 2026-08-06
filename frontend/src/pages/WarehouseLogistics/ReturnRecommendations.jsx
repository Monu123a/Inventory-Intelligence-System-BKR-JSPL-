import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import Button from '../../components/forms/Button';
import styles from '../Warehouse/Warehouse.module.css';

const ReturnRecommendations = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/api/fc-dispatches/recommendations')
      .then(res => {
        // Handle both direct array or wrapped data response
        setRecommendations(Array.isArray(res.data) ? res.data : (res.data.data || []));
      })
      .catch(err => console.error('Error fetching recommendations:', err))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { key: 'product', label: 'Product' },
    { key: 'warehouse', label: 'FC Warehouse' },
    { key: 'daysAging', label: 'Days Aging' },
    { key: 'quantity', label: 'Quantity' },
    { key: 'action', label: 'Action' }
  ];

  return (
    <PageContainer 
      title="Return Recommendations"
      actions={
        <Button 
          variant="primary"
          onClick={() => navigate('/logistics/dispatch')}
        >
          Create New Dispatch
        </Button>
      }
    >
      <div style={{ marginBottom: '1.5rem', color: '#4b5563' }}>
        45-Day Aging FC Inventory Recommendations
      </div>

      <Card noPadding>
        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Analyzing inventory aging...</td>
                </tr>
              ) : recommendations.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '3rem', color: '#6b7280' }}>
                    <svg style={{ margin: '0 auto', height: '3rem', width: '3rem', color: '#9ca3af', marginBottom: '0.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div style={{ fontSize: '1.125rem', fontWeight: '500', color: '#111827' }}>No pending recommendations</div>
                    <div style={{ marginTop: '0.25rem' }}>All inventory within healthy aging limits.</div>
                  </td>
                </tr>
              ) : (
                recommendations.map((rec, index) => {
                  const days = rec.daysSinceDispatch || rec.daysAging;
                  return (
                    <TableRow 
                      key={index} 
                      row={{
                        product: (
                          <div>
                            <div style={{ fontWeight: '500', color: '#111827' }}>{rec.product || rec.productName}</div>
                            {rec.sku && <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{rec.sku}</div>}
                          </div>
                        ),
                        warehouse: rec.warehouse || rec.warehouseName,
                        daysAging: (
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            backgroundColor: days > 60 ? '#fee2e2' : '#fef9c3',
                            color: days > 60 ? '#991b1b' : '#854d0e'
                          }}>
                            {days} days
                          </span>
                        ),
                        quantity: `${rec.quantity || 1} units`,
                        action: (
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <Button variant="secondary" size="small">
                              Initiate Return
                            </Button>
                            <Button 
                              variant="primary" 
                              size="small"
                              onClick={() => navigate('/logistics/dispatch', { state: { prefill: rec } })}
                            >
                              Create Dispatch
                            </Button>
                          </div>
                        )
                      }} 
                      columns={columns} 
                    />
                  );
                })
              )}
            </tbody>
          </DataTable>
        </div>
      </Card>
    </PageContainer>
  );
};

export default ReturnRecommendations;

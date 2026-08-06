import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import styles from '../Warehouse/Warehouse.module.css';

const DispatchDashboard = () => {
  const [dispatches, setDispatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [originFilter, setOriginFilter] = useState('ALL');

  useEffect(() => {
    api.get('/api/fc-dispatches')
      .then(res => {
        if (Array.isArray(res.data)) {
          setDispatches(res.data);
        } else {
          setDispatches([]);
        }
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { key: 'dispatch_number', label: 'Dispatch ID' },
    { key: 'origin', label: 'Origin' },
    { key: 'dispatch_status', label: 'Status' },
    { key: 'created_at', label: 'Date' }
  ];

  const filteredDispatches = dispatches.filter(d => {
    if (originFilter === 'ALL') return true;
    const isCentral = d.source_type === 'CENTRAL_WAREHOUSE';
    if (originFilter === 'CENTRAL') return isCentral;
    if (originFilter === 'BKR') return !isCentral;
    return true;
  });

  return (
    <PageContainer title="FC Dispatch Dashboard">
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <label style={{ fontWeight: '500' }}>Filter by Origin:</label>
        <select 
          value={originFilter}
          onChange={(e) => setOriginFilter(e.target.value)}
          style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="ALL">All</option>
          <option value="BKR">BKR Main Warehouse</option>
          <option value="CENTRAL">Central Warehouse</option>
        </select>
      </div>
      <Card noPadding>
        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading dispatches...</td>
                </tr>
              ) : filteredDispatches.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    No dispatches found.
                  </td>
                </tr>
              ) : (
                filteredDispatches.map(dispatch => (
                  <TableRow 
                    key={dispatch.id} 
                    row={{
                      dispatch_number: dispatch.dispatch_number || dispatch.id,
                      origin: dispatch.source_type === 'CENTRAL_WAREHOUSE' ? 'Central Warehouse' : 'BKR Main',
                      dispatch_status: (
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '12px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          backgroundColor: dispatch.dispatch_status === 'Completed' ? '#dcfce7' : '#fef9c3',
                          color: dispatch.dispatch_status === 'Completed' ? '#166534' : '#854d0e'
                        }}>
                          {dispatch.dispatch_status}
                        </span>
                      ),
                      created_at: dispatch.created_at ? new Date(dispatch.created_at).toLocaleDateString() : '-'
                    }} 
                    columns={columns} 
                  />
                ))
              )}
            </tbody>
          </DataTable>
        </div>
      </Card>
    </PageContainer>
  );
};

export default DispatchDashboard;

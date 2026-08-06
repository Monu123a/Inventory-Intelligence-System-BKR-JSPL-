import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import Button from '../../components/forms/Button';
import styles from '../Warehouse/Warehouse.module.css';

const DamageClaimManager = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchClaims();
  }, []);

  const fetchClaims = () => {
    setLoading(true);
    api.get('/api/damage-claims')
      .then(res => setClaims(Array.isArray(res.data) ? res.data : []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  const handleUpdateStatus = async (id, status) => {
    if (!window.confirm(`Are you sure you want to ${status.toLowerCase()} this claim?`)) return;
    
    try {
      await api.patch(`/api/damage-claims/${id}/status`, { status });
      fetchClaims();
    } catch (err) {
      console.error(err);
      alert('Error updating claim status');
    }
  };

  const columns = [
    { key: 'id', label: 'Claim ID' },
    { key: 'itemDetails', label: 'Item Details' },
    { key: 'date', label: 'Reported Date' },
    { key: 'status', label: 'Status' },
    { key: 'actions', label: 'Actions' }
  ];

  return (
    <PageContainer title="Damage Claims Management">
      <Card noPadding>
        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading claims...</td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    <div style={{ fontSize: '1.125rem', fontWeight: '500', marginBottom: '0.25rem' }}>No damage claims</div>
                    <div style={{ fontSize: '0.875rem' }}>There are currently no damage claims to process.</div>
                  </td>
                </tr>
              ) : (
                claims.map(claim => (
                  <TableRow 
                    key={claim.id} 
                    row={{
                      id: claim.id,
                      itemDetails: (
                        <div>
                          <div style={{ fontWeight: '500', color: '#111827' }}>{claim.item}</div>
                          {claim.description && <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px' }}>{claim.description}</div>}
                        </div>
                      ),
                      date: claim.date ? new Date(claim.date).toLocaleDateString() : '-',
                      status: (
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '12px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          backgroundColor: claim.status === 'APPROVED' ? '#dcfce7' : claim.status === 'REJECTED' ? '#fee2e2' : '#fef9c3',
                          color: claim.status === 'APPROVED' ? '#166534' : claim.status === 'REJECTED' ? '#991b1b' : '#854d0e'
                        }}>
                          {claim.status || 'PENDING'}
                        </span>
                      ),
                      actions: (claim.status === 'PENDING' || !claim.status) ? (
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <Button variant="secondary" size="small" onClick={() => handleUpdateStatus(claim.id, 'APPROVED')} style={{ color: '#166534', borderColor: '#bbf7d0', backgroundColor: '#f0fdf4' }}>
                            Approve
                          </Button>
                          <Button variant="secondary" size="small" onClick={() => handleUpdateStatus(claim.id, 'REJECTED')} style={{ color: '#991b1b', borderColor: '#fecaca', backgroundColor: '#fef2f2' }}>
                            Reject
                          </Button>
                        </div>
                      ) : (
                        <span style={{ color: '#9ca3af', fontStyle: 'italic', fontSize: '0.875rem' }}>Resolved</span>
                      )
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

export default DamageClaimManager;

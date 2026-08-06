import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import { Modal } from '../../components/Modal/Modal';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import styles from '../Warehouse/Warehouse.module.css';

const FCReturnsView = () => {
  const [returns, setReturns] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [newReturn, setNewReturn] = useState({ dispatchId: '', reason: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchReturns();
  }, []);

  const fetchReturns = () => {
    setLoading(true);
    api.get('/api/fc-returns')
      .then(res => setReturns(Array.isArray(res.data) ? res.data : []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  const handleCreateReturn = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/fc-returns', newReturn);
      setShowModal(false);
      setNewReturn({ dispatchId: '', reason: '' });
      fetchReturns();
      alert('Return request created successfully');
    } catch (err) {
      console.error(err);
      alert('Error creating return request');
    }
  };

  const columns = [
    { key: 'id', label: 'Return ID' },
    { key: 'dispatchId', label: 'Dispatch ID' },
    { key: 'reason', label: 'Reason' },
    { key: 'status', label: 'Status' }
  ];

  return (
    <PageContainer 
      title="FC Returns"
      actions={<Button variant="primary" onClick={() => setShowModal(true)}>+ New Return Request</Button>}
    >
      <Card noPadding>
        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading returns...</td>
                </tr>
              ) : returns.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    No return requests found.
                  </td>
                </tr>
              ) : (
                returns.map(ret => (
                  <TableRow 
                    key={ret.id} 
                    row={{
                      id: ret.id,
                      dispatchId: ret.dispatchId,
                      reason: ret.reason,
                      status: (
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '12px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          backgroundColor: ret.status === 'APPROVED' ? '#dcfce7' : ret.status === 'PENDING' ? '#fef9c3' : '#f3f4f6',
                          color: ret.status === 'APPROVED' ? '#166534' : ret.status === 'PENDING' ? '#854d0e' : '#374151'
                        }}>
                          {ret.status || 'PENDING'}
                        </span>
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

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Initiate FC Return">
        <form onSubmit={handleCreateReturn} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input 
            label="Dispatch ID" 
            placeholder="e.g. DISP-1234"
            value={newReturn.dispatchId} 
            onChange={(e) => setNewReturn({...newReturn, dispatchId: e.target.value})} 
            required 
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Reason for Return</label>
            <textarea 
              value={newReturn.reason}
              onChange={(e) => setNewReturn({...newReturn, reason: e.target.value})}
              placeholder="Explain why items are being returned"
              style={{ width: '100%', minHeight: '100px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
              required
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            <Button type="button" variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button type="submit" variant="primary">Submit Return</Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
};

export default FCReturnsView;

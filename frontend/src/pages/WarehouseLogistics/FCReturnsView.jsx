import React, { useState, useEffect, useRef } from 'react';
import api from '../../services/api';
import { useQueryClient } from '@tanstack/react-query';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import { Modal } from '../../components/Modal/Modal';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import toast from 'react-hot-toast';
import useCompanyStore from '../../stores/useCompanyStore';
import styles from '../Warehouse/Warehouse.module.css';

const FCReturnsView = () => {
  const queryClient = useQueryClient();
  const [returns, setReturns] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const idempotencyKeyRef = useRef(window.crypto.randomUUID());
  const [newReturn, setNewReturn] = useState({ dispatchId: '', dispatchItemId: '', quantity: 1, reason: '' });
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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
    
    if (!newReturn.dispatchId || !newReturn.dispatchItemId || parseInt(newReturn.quantity) <= 0) {
      toast.error('Invalid return payload: Missing dispatch details or quantity');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        idempotency_key: idempotencyKeyRef.current,
        dispatch_id: parseInt(newReturn.dispatchId),
        items: [
          {
            dispatch_item_id: parseInt(newReturn.dispatchItemId),
            quantity: parseInt(newReturn.quantity),
            return_reason: newReturn.reason
          }
        ]
      };

      await api.post('/api/fc-returns', payload);
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['fc-returns'] });
      setShowModal(false);
      setNewReturn({ dispatchId: '', dispatchItemId: '', quantity: 1, reason: '' });
      idempotencyKeyRef.current = window.crypto.randomUUID();
      fetchReturns();
      toast.success('Return request created successfully');
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || 'Error creating return request');
    } finally {
      setSubmitting(false);
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
            placeholder="e.g. 1234"
            value={newReturn.dispatchId} 
            onChange={(e) => setNewReturn({...newReturn, dispatchId: e.target.value})} 
            required 
          />
          <Input 
            label="Dispatch Item ID" 
            placeholder="e.g. 1"
            value={newReturn.dispatchItemId} 
            onChange={(e) => setNewReturn({...newReturn, dispatchItemId: e.target.value})} 
            required 
          />
          <Input 
            label="Quantity" 
            type="number"
            min="1"
            value={newReturn.quantity} 
            onChange={(e) => setNewReturn({...newReturn, quantity: e.target.value})} 
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
            <Button type="submit" variant="primary" disabled={submitting}>Submit Return</Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
};

export default FCReturnsView;

import React, { useEffect, useState } from 'react';
import { FiPlus, FiEye, FiCheck, FiX } from 'react-icons/fi';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';
import CreateReturnModal from './CreateReturnModal';
import ViewReturnModal from './ViewReturnModal';
import styles from './SalesReturnsPage.module.css';

export default function SalesReturnsPage() {
  const currentCompany = useCompanyStore(state => state.currentCompany);
  
  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [viewReturn, setViewReturn] = useState(null);

  useEffect(() => {
    if (currentCompany?.id) {
      fetchReturns();
    }
  }, [currentCompany]);

  const fetchReturns = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/sales-returns/');
      setReturns(response.data || []);
    } catch (err) {
      console.error('Failed to fetch sales returns:', err);
      setError('Failed to load sales returns.');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (id, status) => {
    try {
      if (status === 'Completed') {
         await api.post(`/api/sales-returns/${id}/complete`);
      } else if (status === 'Cancelled') {
         await api.post(`/api/sales-returns/${id}/cancel`);
      }
      fetchReturns();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to update status');
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Sales Returns</h2>
        <button 
          className={styles.primaryButton}
          onClick={() => setShowCreateModal(true)}
        >
          <FiPlus /> New Return
        </button>
      </div>

      {error && <div className={styles.errorText} style={{color: 'red', marginBottom: '16px'}}>{error}</div>}

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Return No</th>
              <th>Date</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Total Amount</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" className={styles.empty}>Loading...</td>
              </tr>
            ) : returns.length === 0 ? (
              <tr>
                <td colSpan="6" className={styles.empty}>No sales returns found.</td>
              </tr>
            ) : (
              returns.map((ret) => (
                <tr key={ret.id}>
                  <td><strong>{ret.return_number}</strong></td>
                  <td>{new Date(ret.return_date).toLocaleDateString()}</td>
                  <td>{ret.customer_name || 'Walk-in Customer'}</td>
                  <td>
                    <span className={`${styles.badge} ${styles[ret.status?.toLowerCase()] || ''}`}>
                      {ret.status}
                    </span>
                  </td>
                  <td>₹ {ret.grand_total?.toFixed(2)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button className={styles.actionButton} onClick={() => setViewReturn(ret)}>
                        <FiEye /> View
                      </button>
                      
                      {ret.status === 'Draft' && (
                        <>
                          <button 
                            className={styles.actionButton} 
                            style={{ color: 'green' }}
                            onClick={() => handleStatusUpdate(ret.id, 'Completed')}
                          >
                            <FiCheck /> Complete
                          </button>
                          <button 
                            className={styles.actionButton} 
                            style={{ color: 'red' }}
                            onClick={() => handleStatusUpdate(ret.id, 'Cancelled')}
                          >
                            <FiX /> Cancel
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showCreateModal && (
        <CreateReturnModal 
          onClose={() => setShowCreateModal(false)} 
          onSuccess={() => {
            setShowCreateModal(false);
            fetchReturns();
          }}
        />
      )}

      <ViewReturnModal 
        returnDetails={viewReturn} 
        onClose={() => setViewReturn(null)} 
      />
    </div>
  );
}

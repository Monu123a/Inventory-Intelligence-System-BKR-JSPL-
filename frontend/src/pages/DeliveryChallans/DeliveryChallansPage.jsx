import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiPlus, FiEye, FiPrinter, FiFileText } from 'react-icons/fi';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';
import styles from './DeliveryChallansPage.module.css';

export default function DeliveryChallansPage() {
  const navigate = useNavigate();
  const currentCompany = useCompanyStore(state => state.currentCompany);
  
  const [challans, setChallans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (currentCompany?.id) {
      fetchChallans();
    }
  }, [currentCompany]);

  const fetchChallans = async () => {
    setLoading(true);
    setError('');
    try {
      // Pass company_id context handled by axios interceptor
      const response = await api.get('/api/delivery-challans/');
      setChallans(response.data || []);
    } catch (err) {
      console.error('Failed to fetch challans:', err);
      setError('Failed to load delivery challans.');
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = (id) => {
    navigate(`/delivery-challans/${id}`);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Delivery Challans</h2>
        <button 
          className={styles.primaryButton}
          onClick={() => navigate('/delivery-challans/create')}
        >
          <FiPlus /> Create Challan
        </button>
      </div>

      {error && <div className={styles.errorText} style={{color: 'red', marginBottom: '16px'}}>{error}</div>}

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Challan No</th>
              <th>Date</th>
              <th>Status</th>
              <th>Created By</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="5" className={styles.empty}>Loading...</td>
              </tr>
            ) : challans.length === 0 ? (
              <tr>
                <td colSpan="5" className={styles.empty}>No delivery challans found.</td>
              </tr>
            ) : (
              challans.map((challan) => (
                <tr key={challan.id}>
                  <td><strong>{challan.challan_number}</strong></td>
                  <td>{new Date(challan.challan_date).toLocaleDateString()}</td>
                  <td>
                    <span className={`${styles.badge} ${styles[challan.status?.toLowerCase()] || ''}`}>
                      {challan.status}
                    </span>
                  </td>
                  <td>{challan.created_by_name || 'System'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button 
                        className={styles.actionButton}
                        onClick={() => navigate(`/delivery-challans/${challan.id}`)}
                      >
                        <FiEye /> View
                      </button>
                      <button 
                        className={styles.actionButton}
                        onClick={() => handlePrint(challan.id)}
                      >
                        <FiPrinter /> Print
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

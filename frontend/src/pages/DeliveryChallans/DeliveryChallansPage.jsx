import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiPlus, FiEye, FiPrinter } from 'react-icons/fi';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import Button from '../../components/forms/Button';
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
      const response = await api.get('/api/delivery-challans/');
      setChallans(response.data || []);
    } catch (err) {
      console.error('Failed to fetch challans:', err);
      setError('Failed to load delivery challans.');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { 
      key: 'challan_number', 
      label: 'Challan No', 
      render: (val) => <strong>{val}</strong> 
    },
    { 
      key: 'challan_date', 
      label: 'Date', 
      render: (val) => new Date(val).toLocaleDateString() 
    },
    { 
      key: 'status', 
      label: 'Status', 
      render: (val) => <span className={`${styles.badge} ${styles[val?.toLowerCase()] || ''}`}>{val}</span> 
    },
    { 
      key: 'created_by_name', 
      label: 'Created By', 
      render: (val) => val || 'System' 
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, challan) => (
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className={styles.actionButton}
            onClick={() => navigate(`/delivery-challans/${challan.id}`)}
          >
            <FiEye /> View
          </button>
          <button 
            className={styles.actionButton}
            onClick={() => navigate(`/delivery-challans/${challan.id}`)}
          >
            <FiPrinter /> Print
          </button>
        </div>
      )
    }
  ];

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Delivery Challans</h2>
        <Button 
          variant="primary"
          onClick={() => navigate('/delivery-challans/create')}
        >
          <FiPlus /> Create Challan
        </Button>
      </div>

      {error && <div className={styles.errorText} style={{color: 'red', marginBottom: '16px'}}>{error}</div>}

      <div className={styles.tableWrapper}>
        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className={styles.empty} style={{textAlign: 'center', padding: '2rem'}}>Loading...</td>
              </tr>
            ) : challans.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className={styles.empty} style={{textAlign: 'center', padding: '2rem'}}>No delivery challans found.</td>
              </tr>
            ) : (
              challans.map((challan) => (
                <TableRow key={challan.id} row={challan} columns={columns} />
              ))
            )}
          </tbody>
        </DataTable>
      </div>
    </div>
  );
}

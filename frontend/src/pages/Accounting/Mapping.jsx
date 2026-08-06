import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { useNotificationStore } from '../../stores/notificationStore';
import styles from './Mapping.module.css';

const MAPPING_TYPES = ['Ledger', 'Product', 'Company'];

const Mapping = () => {
  const [activeTab, setActiveTab] = useState(MAPPING_TYPES[0]);
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const addNotification = useNotificationStore(state => state.addNotification);
  
  const [erpRef, setErpRef] = useState('');
  const [accName, setAccName] = useState('');

  const fetchMappings = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/accounting/mapping');
      setMappings(res.data);
    } catch (err) {
      addNotification({ type: 'error', message: 'Failed to fetch mappings' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!erpRef || !accName) return;
    
    try {
      await api.post('/api/accounting/mapping', {
        mapping_type: activeTab,
        erp_reference: erpRef,
        accounting_name: accName
      });
      addNotification({ type: 'success', message: 'Mapping saved successfully' });
      setErpRef('');
      setAccName('');
      fetchMappings();
    } catch (err) {
      addNotification({ type: 'error', message: 'Failed to save mapping' });
    }
  };

  const currentMappings = mappings.filter(m => m.mapping_type === activeTab);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>ERP to Accounting Mapping</h1>
        <p className={styles.subtitle}>Map your internal ERP names (like Customers, Items) to their exact names in Tally.</p>
      </header>

      <div className={styles.tabs}>
        {MAPPING_TYPES.map(type => (
          <button
            key={type}
            className={`${styles.tab} ${activeTab === type ? styles.active : ''}`}
            onClick={() => { setActiveTab(type); setErpRef(''); setAccName(''); }}
          >
            {type} Mappings
          </button>
        ))}
      </div>

      <div className={styles.contentWrapper}>
        <form className={styles.formGrid} onSubmit={handleSave}>
          <div className={styles.formGroup}>
            <label className={styles.label}>ERP Reference ({activeTab})</label>
            <input 
              className={styles.input}
              placeholder={`e.g., ${activeTab === 'Ledger' ? 'Cash Customer' : 'SKU-01'}`}
              value={erpRef}
              onChange={e => setErpRef(e.target.value)}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Accounting Name (Tally)</label>
            <input 
              className={styles.input}
              placeholder={`e.g., ${activeTab === 'Ledger' ? 'Cash Sales' : 'Product A'}`}
              value={accName}
              onChange={e => setAccName(e.target.value)}
            />
          </div>
          <button type="submit" className={styles.btnPrimary} disabled={!erpRef || !accName}>
            Save Mapping
          </button>
        </form>

        <table className={styles.table}>
          <thead>
            <tr>
              <th>ERP Reference</th>
              <th>Accounting Name</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="2" style={{ textAlign: 'center' }}>Loading...</td></tr>
            ) : currentMappings.length === 0 ? (
              <tr><td colSpan="2" style={{ textAlign: 'center' }}>No mappings defined yet.</td></tr>
            ) : (
              currentMappings.map((m, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 500 }}>{m.erp_reference}</td>
                  <td>{m.accounting_name}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Mapping;

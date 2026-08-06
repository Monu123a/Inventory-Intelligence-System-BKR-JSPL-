import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { useNotificationStore } from '../../stores/notificationStore';
import styles from './Configuration.module.css';

const Configuration = () => {
  const [config, setConfig] = useState({
    default_sales_ledger: '',
    default_godown: '',
    round_off_ledger: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const addNotification = useNotificationStore(state => state.addNotification);

  const fetchConfig = async () => {
    try {
      const res = await api.get('/api/accounting/configuration');
      if (res.data) {
        setConfig({
          default_sales_ledger: res.data.default_sales_ledger || '',
          default_godown: res.data.default_godown || '',
          round_off_ledger: res.data.round_off_ledger || ''
        });
      }
    } catch (err) {
      addNotification({ type: 'error', message: 'Failed to fetch configuration' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post('/api/accounting/configuration', config);
      addNotification({ type: 'success', message: 'Configuration saved successfully' });
    } catch (err) {
      addNotification({ type: 'error', message: 'Failed to save configuration' });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (e) => {
    setConfig(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  if (loading) {
    return <div className={styles.container}>Loading...</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Export Settings</h1>
        <p className={styles.subtitle}>Configure default values used when generating accounting exports.</p>
      </header>

      <div className={styles.card}>
        <form onSubmit={handleSave}>
          
          <h2 className={styles.sectionTitle} style={{ marginTop: 0 }}>Tally Defaults</h2>
          
          <div className={styles.formGroup}>
            <label className={styles.label}>Default Sales Ledger</label>
            <input 
              name="default_sales_ledger"
              className={styles.input}
              value={config.default_sales_ledger}
              onChange={handleChange}
              placeholder="e.g., Sales Account"
            />
            <p className={styles.helpText}>Fallback ledger if no specific product mapping is found.</p>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Default Godown</label>
            <input 
              name="default_godown"
              className={styles.input}
              value={config.default_godown}
              onChange={handleChange}
              placeholder="e.g., Main Location"
            />
            <p className={styles.helpText}>The default inventory godown where stock will be deducted from.</p>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Round Off Ledger</label>
            <input 
              name="round_off_ledger"
              className={styles.input}
              value={config.round_off_ledger}
              onChange={handleChange}
              placeholder="e.g., Round Off"
            />
            <p className={styles.helpText}>Ledger used to balance fraction amounts (e.g. 0.02).</p>
          </div>

          <button type="submit" className={styles.btnPrimary} disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Configuration;

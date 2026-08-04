import React, { useState, useEffect } from 'react';
import { FiDownload, FiPlay, FiAlertCircle } from 'react-icons/fi';
import api from '../../services/api';
import { useNotificationStore } from '../../stores/notificationStore';
import styles from './ExportCenter.module.css';

const ExportCenter = () => {
  const [stats, setStats] = useState({ pending_exports: 0, generated_today: 0, failed_exports: 0, total_value: 0 });
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState('all');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [generating, setGenerating] = useState(false);
  const addNotification = useNotificationStore(state => state.addNotification);

  const fetchStats = async () => {
    try {
      const res = await api.get('/accounting/statistics');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats', err);
    }
  };

  const fetchInvoices = async (filterProfile) => {
    setLoading(true);
    try {
      const res = await api.get(`/accounting/invoices?profile=${filterProfile}`);
      setInvoices(res.data);
      // reset selection
      setSelectedIds(new Set());
    } catch (err) {
      addNotification({ type: 'error', message: 'Failed to fetch invoices' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchInvoices(profile);
  }, [profile]);

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const allSelectable = invoices.filter(i => i.export_status === 'Ready' || i.export_status === 'Failed').map(i => i.id);
      setSelectedIds(new Set(allSelectable));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectRow = (id) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleGenerate = async () => {
    if (selectedIds.size === 0) return;
    setGenerating(true);
    try {
      const res = await api.post('/accounting/export/batch', {
        sale_ids: Array.from(selectedIds)
      });
      addNotification({ type: 'success', message: `Export batch created successfully. Status: ${res.data.status}` });
      fetchStats();
      fetchInvoices(profile);
    } catch (err) {
      addNotification({ type: 'error', message: err.response?.data?.detail || 'Failed to generate export batch' });
    } finally {
      setGenerating(false);
    }
  };

  const formatCurrency = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Export Center</h1>
      </header>

      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>Pending Exports</span>
          <span className={styles.kpiValue}>{stats.pending_exports}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>Generated Today</span>
          <span className={styles.kpiValue}>{stats.generated_today}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>Failed Exports</span>
          <span className={styles.kpiValue} style={{ color: stats.failed_exports > 0 ? '#b91c1c' : 'inherit' }}>
            {stats.failed_exports}
          </span>
        </div>
      </div>

      <div className={styles.contentWrapper}>
        <div className={styles.toolbar}>
          <div className={styles.filterGroup}>
            {['all', 'today', 'yesterday', 'pending', 'failed'].map(p => (
              <button
                key={p}
                className={`${styles.filterBtn} ${profile === p ? styles.active : ''}`}
                onClick={() => setProfile(p)}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>

          <div className={styles.actionGroup}>
            <button 
              className={styles.btnPrimary} 
              disabled={selectedIds.size === 0 || generating}
              onClick={handleGenerate}
            >
              <FiPlay />
              {generating ? 'Generating...' : `Generate XML (${selectedIds.size})`}
            </button>
          </div>
        </div>

        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th style={{ width: '40px' }}>
                  <input 
                    type="checkbox" 
                    onChange={handleSelectAll}
                    checked={invoices.length > 0 && selectedIds.size === invoices.filter(i => i.export_status === 'Ready' || i.export_status === 'Failed').length}
                  />
                </th>
                <th>Invoice No</th>
                <th>Date</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '24px' }}>Loading...</td></tr>
              ) : invoices.length === 0 ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '24px' }}>No invoices found.</td></tr>
              ) : (
                invoices.map(inv => {
                  const isSelectable = inv.export_status === 'Ready' || inv.export_status === 'Failed';
                  const isSelected = selectedIds.has(inv.id);
                  return (
                    <tr key={inv.id} className={isSelected ? styles.selected : ''}>
                      <td>
                        {isSelectable && (
                          <input 
                            type="checkbox" 
                            checked={isSelected}
                            onChange={() => handleSelectRow(inv.id)}
                          />
                        )}
                      </td>
                      <td style={{ fontWeight: 500 }}>{inv.invoice_number}</td>
                      <td>{new Date(inv.invoice_date).toLocaleDateString()}</td>
                      <td>{inv.customer_name}</td>
                      <td>{formatCurrency(inv.grand_total)}</td>
                      <td>
                        <span className={`${styles.badge} ${styles[inv.export_status.toLowerCase().replace(' ', '')] || ''}`}>
                          {inv.export_status}
                        </span>
                        {inv.last_error && (
                          <span title={inv.last_error} style={{ marginLeft: 8, color: '#ef4444', cursor: 'help' }}>
                            <FiAlertCircle />
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ExportCenter;

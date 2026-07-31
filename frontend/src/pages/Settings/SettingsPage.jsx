import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import styles from './SettingsPage.module.css';
import { FiSave, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    legal_name: '',
    gstin: '',
    address: '',
    state: '',
    state_code: '',
    email: '',
    phone: '',
    logo_url: '',
    bank_details: { bank_name: '', account_no: '', ifsc: '', branch: '' },
    declaration: '',
    terms_of_delivery_default: '',
    tally_enabled: false,
    tally_endpoint_url: '',
    tally_payload_format: 'XML'
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/settings/');
      if (res.data) {
        setSettings((prev) => ({
          ...prev,
          ...res.data,
          bank_details: {
            ...prev.bank_details,
            ...(res.data.bank_details || {})
          }
        }));
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      showMessage('Failed to fetch settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleBankChange = (e) => {
    const { name, value } = e.target;
    setSettings((prev) => ({
      ...prev,
      bank_details: {
        ...prev.bank_details,
        [name]: value
      }
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      await api.put('/api/settings/', settings);
      showMessage('Settings saved successfully', 'success');
    } catch (error) {
      console.error('Error saving settings:', error);
      showMessage('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  if (loading) {
    return <div className={styles.loading}>Loading settings...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Settings</h1>
        <button className={styles.saveBtnTop} onClick={handleSave} disabled={saving}>
          <FiSave /> {saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {message.text && (
        <div className={`${styles.message} ${styles[message.type]}`}>
          {message.type === 'success' ? <FiCheckCircle /> : <FiAlertCircle />}
          {message.text}
        </div>
      )}

      <form className={styles.form} onSubmit={handleSave}>
        {/* Company Profile */}
        <section className={styles.section}>
          <h2>Company Profile</h2>
          <div className={styles.grid}>
            <div className={styles.formGroup}>
              <label>Legal Name</label>
              <input type="text" name="legal_name" value={settings.legal_name || ''} onChange={handleChange} />
            </div>
            <div className={styles.formGroup}>
              <label>GSTIN</label>
              <input type="text" name="gstin" value={settings.gstin || ''} onChange={handleChange} />
            </div>
            <div className={styles.formGroup}>
              <label>Email</label>
              <input type="email" name="email" value={settings.email || ''} onChange={handleChange} />
            </div>
            <div className={styles.formGroup}>
              <label>Phone</label>
              <input type="text" name="phone" value={settings.phone || ''} onChange={handleChange} />
            </div>
            <div className={styles.formGroup}>
              <label>State</label>
              <input type="text" name="state" value={settings.state || ''} onChange={handleChange} />
            </div>
            <div className={styles.formGroup}>
              <label>State Code</label>
              <input type="text" name="state_code" value={settings.state_code || ''} onChange={handleChange} />
            </div>
            <div className={styles.formGroup}>
              <label>Logo URL</label>
              <input type="text" name="logo_url" value={settings.logo_url || ''} onChange={handleChange} />
            </div>
            <div className={`${styles.formGroup} ${styles.fullWidth}`}>
              <label>Address</label>
              <textarea name="address" value={settings.address || ''} onChange={handleChange} rows="3" />
            </div>
          </div>
        </section>

        {/* Bank Details */}
        <section className={styles.section}>
          <h2>Bank Details</h2>
          <div className={styles.grid}>
            <div className={styles.formGroup}>
              <label>Bank Name</label>
              <input type="text" name="bank_name" value={settings.bank_details?.bank_name || ''} onChange={handleBankChange} />
            </div>
            <div className={styles.formGroup}>
              <label>Account Number</label>
              <input type="text" name="account_no" value={settings.bank_details?.account_no || ''} onChange={handleBankChange} />
            </div>
            <div className={styles.formGroup}>
              <label>IFSC Code</label>
              <input type="text" name="ifsc" value={settings.bank_details?.ifsc || ''} onChange={handleBankChange} />
            </div>
            <div className={styles.formGroup}>
              <label>Branch</label>
              <input type="text" name="branch" value={settings.bank_details?.branch || ''} onChange={handleBankChange} />
            </div>
          </div>
        </section>

        {/* Invoice Defaults */}
        <section className={styles.section}>
          <h2>Invoice Defaults</h2>
          <div className={styles.grid}>
            <div className={`${styles.formGroup} ${styles.fullWidth}`}>
              <label>Declaration</label>
              <textarea name="declaration" value={settings.declaration || ''} onChange={handleChange} rows="3" />
            </div>
            <div className={`${styles.formGroup} ${styles.fullWidth}`}>
              <label>Default Terms of Delivery</label>
              <textarea name="terms_of_delivery_default" value={settings.terms_of_delivery_default || ''} onChange={handleChange} rows="3" />
            </div>
          </div>
        </section>

        {/* Tally Integration */}
        <section className={styles.section}>
          <h2>Tally Integration</h2>
          <div className={styles.grid}>
            <div className={styles.formGroupToggle}>
              <label className={styles.toggleLabel}>
                <span className={styles.toggleText}>Enable Tally Integration</span>
                <div className={styles.toggleSwitch}>
                  <input type="checkbox" name="tally_enabled" checked={settings.tally_enabled || false} onChange={handleChange} />
                  <span className={styles.slider}></span>
                </div>
              </label>
            </div>
            
            {settings.tally_enabled && (
              <>
                <div className={styles.formGroup}>
                  <label>Tally Endpoint URL</label>
                  <input type="text" name="tally_endpoint_url" value={settings.tally_endpoint_url || ''} onChange={handleChange} placeholder="http://localhost:9000" />
                </div>
                <div className={styles.formGroup}>
                  <label>Payload Format</label>
                  <select name="tally_payload_format" value={settings.tally_payload_format || 'XML'} onChange={handleChange}>
                    <option value="XML">XML</option>
                    <option value="JSON">JSON</option>
                  </select>
                </div>
              </>
            )}
          </div>
        </section>

        <div className={styles.actions}>
          <button type="submit" className={styles.saveBtn} disabled={saving}>
            <FiSave /> {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { einvoiceService } from '../../services/einvoice';
import styles from './SettingsPage.module.css';
import { FiSave, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';
import { useQueryClient } from '@tanstack/react-query';

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
    tally_payload_format: 'XML',
    export_internal_distribution_to_accounting: false
  });

  const [einvoiceSettings, setEinvoiceSettings] = useState({
    einvoice_enabled: false,
    einvoice_provider: 'CLEARTAX',
    environment: 'sandbox',
    gstin: '',
    auth_token: '',
    client_id: '',
    client_secret: '',
    auto_generate_on_pos: false
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const queryClient = useQueryClient();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const [res, einvRes] = await Promise.all([
        api.get('/api/settings/'),
        einvoiceService.getSettings().catch((e) => {
          console.warn('Could not fetch einvoice settings:', e);
          return null;
        })
      ]);
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
      if (einvRes) {
        setEinvoiceSettings((prev) => ({
          ...prev,
          ...einvRes
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

  const handleEinvoiceChange = (e) => {
    const { name, value, type, checked } = e.target;
    setEinvoiceSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      await Promise.all([
        api.put('/api/settings/', settings),
        einvoiceService.updateSettings(einvoiceSettings)
      ]);
      queryClient.invalidateQueries({ queryKey: ['companies'] });
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
                <div className={styles.formGroupToggle}>
                  <label className={styles.toggleLabel}>
                    <span className={styles.toggleText}>Export Internal Distribution to Accounting</span>
                    <div className={styles.toggleSwitch}>
                      <input type="checkbox" name="export_internal_distribution_to_accounting" checked={settings.export_internal_distribution_to_accounting || false} onChange={handleChange} />
                      <span className={styles.slider}></span>
                    </div>
                  </label>
                </div>
              </>
            )}
          </div>
        </section>

        {/* E-Invoicing (GST B2B) Integration */}
        <section className={styles.section}>
          <h2>E-Invoicing (GST B2B IRN)</h2>
          <div className={styles.grid}>
            <div className={styles.formGroupToggle}>
              <label className={styles.toggleLabel}>
                <span className={styles.toggleText}>Enable E-Invoicing (IRN & Signed QR)</span>
                <div className={styles.toggleSwitch}>
                  <input
                    type="checkbox"
                    name="einvoice_enabled"
                    checked={einvoiceSettings.einvoice_enabled || false}
                    onChange={handleEinvoiceChange}
                  />
                  <span className={styles.slider}></span>
                </div>
              </label>
            </div>

            {einvoiceSettings.einvoice_enabled && (
              <>
                <div className={styles.formGroup}>
                  <label>E-Invoice Provider (GSP/ASP)</label>
                  <select
                    name="einvoice_provider"
                    value={einvoiceSettings.einvoice_provider || 'CLEARTAX'}
                    onChange={handleEinvoiceChange}
                  >
                    <option value="CLEARTAX">ClearTax API</option>
                    <option value="MASTERS_INDIA">Masters India</option>
                    <option value="SANDBOX">Simulated Sandbox (Testing Mode)</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label>Environment</label>
                  <select
                    name="environment"
                    value={einvoiceSettings.environment || 'sandbox'}
                    onChange={handleEinvoiceChange}
                  >
                    <option value="sandbox">Sandbox / Staging</option>
                    <option value="production">Production (Live Government IRP)</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label>Provider Auth Token / API Key</label>
                  <input
                    type="password"
                    name="auth_token"
                    value={einvoiceSettings.auth_token || ''}
                    onChange={handleEinvoiceChange}
                    placeholder="Enter GSP Auth Token"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label>Registered GSTIN for E-Invoicing</label>
                  <input
                    type="text"
                    name="gstin"
                    value={einvoiceSettings.gstin || ''}
                    onChange={handleEinvoiceChange}
                    placeholder="15-character GSTIN"
                  />
                </div>

                {einvoiceSettings.einvoice_provider === 'MASTERS_INDIA' && (
                  <>
                    <div className={styles.formGroup}>
                      <label>Client ID</label>
                      <input
                        type="text"
                        name="client_id"
                        value={einvoiceSettings.client_id || ''}
                        onChange={handleEinvoiceChange}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Client Secret</label>
                      <input
                        type="password"
                        name="client_secret"
                        value={einvoiceSettings.client_secret || ''}
                        onChange={handleEinvoiceChange}
                      />
                    </div>
                  </>
                )}

                <div className={styles.formGroupToggle}>
                  <label className={styles.toggleLabel}>
                    <span className={styles.toggleText}>Auto-Generate IRN on B2B POS Checkout</span>
                    <div className={styles.toggleSwitch}>
                      <input
                        type="checkbox"
                        name="auto_generate_on_pos"
                        checked={einvoiceSettings.auto_generate_on_pos || false}
                        onChange={handleEinvoiceChange}
                      />
                      <span className={styles.slider}></span>
                    </div>
                  </label>
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

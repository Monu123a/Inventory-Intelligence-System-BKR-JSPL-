import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';
import { useWarehouses } from '../../hooks/useWarehouses';
import { useUsers } from '../../hooks/useUsers';
import { FiSave, FiSearch, FiPlus, FiTrash2, FiUser, FiTool, FiBox, FiCheckCircle } from 'react-icons/fi';
import styles from './CreateServicePage.module.css';
import { useNotificationStore } from '../../stores/notificationStore';

export default function CreateServicePage() {
  const navigate = useNavigate();
  const currentCompany = useCompanyStore(state => state.currentCompany);
  const addNotification = useNotificationStore(state => state.addNotification);
  
  const { data: warehouses } = useWarehouses();
  const { data: users } = useUsers();
  
  const [sales, setSales] = useState([]);
  const [selectedSaleId, setSelectedSaleId] = useState('');
  const [saleItems, setSaleItems] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState('');
  
  const [formData, setFormData] = useState({
    source_type: 'manual',
    customer_name: '',
    phone: '',
    product_name: '',
    brand: 'Pond',
    custom_brand: '',
    complaint: '',
    service_type: 'Repair',
    service_location: 'Workshop',
    workshop_id: '',
    assigned_to: ''
  });
  
  const [items, setItems] = useState([
    { item_name: 'Initial Diagnosis / Service Charge', product_sku: '', qty: 1, rate: 0, amount: 0 }
  ]);
  
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Set default workshop when loaded
  useEffect(() => {
    if (warehouses && warehouses.length > 0 && !formData.workshop_id) {
      setFormData(prev => ({ ...prev, workshop_id: warehouses[0].id }));
    }
  }, [warehouses, formData.workshop_id]);

  // Load Invoices for the "From Invoice" mode
  useEffect(() => {
    if (currentCompany?.id && formData.source_type === 'invoice') {
      setLoading(true);
      api.get('/api/pos/history?limit=50')
        .then(res => setSales(res.data?.items || res.data || []))
        .catch(err => {
          console.error(err);
          setError('Failed to load past invoices.');
        })
        .finally(() => setLoading(false));
    }
  }, [currentCompany, formData.source_type]);

  useEffect(() => {
    if (selectedSaleId) {
      setLoading(true);
      api.get(`/api/pos/sales/${selectedSaleId}`)
        .then(res => {
          const invoice = res.data?.receipt;
          if (invoice && invoice.items) {
            setSaleItems(invoice.items);
            setSelectedItemId('');
            if (invoice.customer_name) {
              setFormData(prev => ({
                ...prev,
                customer_name: invoice.customer_name,
                phone: invoice.customer_mobile || prev.phone
              }));
            }
          }
        })
        .catch(err => {
          console.error(err);
          setError('Failed to load invoice items.');
          setSaleItems([]);
          setSelectedItemId('');
        })
        .finally(() => setLoading(false));
    } else {
      setSaleItems([]);
      setSelectedItemId('');
    }
  }, [selectedSaleId]);

  // Handle auto-fill when an item is selected from an invoice
  useEffect(() => {
    if (selectedItemId && formData.source_type === 'invoice') {
      const selectedItem = saleItems.find(i => i.id === parseInt(selectedItemId));
      if (selectedItem) {
        setFormData(prev => ({
          ...prev,
          product_name: selectedItem.product_name,
          brand: 'Internal' 
        }));
        
        setItems([
          { 
            item_name: `Service for ${selectedItem.product_name}`, 
            product_sku: selectedItem.sku || '', 
            qty: 1, 
            rate: 0, 
            amount: 0 
          }
        ]);
      }
    }
  }, [selectedItemId, saleItems, formData.source_type]);

  const handleSourceToggle = (source) => {
    setFormData({ ...formData, source_type: source });
    if (source === 'manual') {
      setSelectedSaleId('');
      setSelectedItemId('');
    }
  };

  const handleAddItem = () => {
    setItems([...items, { item_name: '', product_sku: '', qty: 1, rate: 0, amount: 0 }]);
  };

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index, field, value) => {
    const newItems = [...items];
    newItems[index][field] = value;
    if (field === 'qty' || field === 'rate') {
      newItems[index].amount = (parseFloat(newItems[index].qty) || 0) * (parseFloat(newItems[index].rate) || 0);
    }
    setItems(newItems);
  };

  const handleCreate = async () => {
    // Strict Validation
    if (!formData.customer_name.trim()) return setError('Customer Name is required.');
    if (!formData.product_name.trim()) return setError('Product Name / Machine Type is required.');
    if (!formData.complaint.trim() || formData.complaint.trim().length < 5) return setError('Complaint description must be at least 5 characters long.');
    if (!formData.workshop_id) return setError('Please select a Workshop location.');
    if (items.length === 0) return setError('At least one service item/diagnostic charge is required.');
    
    for (let i=0; i<items.length; i++) {
      if (!items[i].item_name.trim()) return setError(`Item #${i+1} is missing a name.`);
      if (items[i].qty <= 0) return setError(`Item #${i+1} quantity must be greater than 0.`);
    }

    setCreating(true);
    setError('');
    
    try {
      const selectedSale = formData.source_type === 'invoice' ? sales.find(s => s.id === parseInt(selectedSaleId)) : null;

      const payload = {
        customer_name: formData.customer_name,
        customer_mobile: formData.phone,
        source_type: formData.source_type,
        source_invoice_id: selectedSale?.bill_number || null,
        product_name: formData.product_name,
        brand: formData.brand === 'Others' ? formData.custom_brand : formData.brand,
        complaint: formData.complaint,
        service_type: formData.service_type,
        service_location: formData.service_location,
        workshop_id: parseInt(formData.workshop_id),
        assigned_to: formData.assigned_to ? parseInt(formData.assigned_to) : null,
        items: items.map(i => ({
          item_name: i.item_name,
          product_sku: i.product_sku.trim() || null,
          qty: parseFloat(i.qty),
          rate: parseFloat(i.rate)
        }))
      };
      
      const response = await api.post('/api/bkr-services/job-cards', payload);
      
      addNotification({
        type: 'success',
        title: 'Service Created',
        message: 'Service record and job card initialized successfully.'
      });
      
      navigate(`/services/job-cards/${response.data.id}`);
    } catch (err) {
      console.error(err);
      let errorMessage = 'Failed to create Service Record';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map(e => `${e.loc?.slice(-1)?.[0] || 'Field'}: ${e.msg}`).join(', ');
        }
      }
      setError(errorMessage);
      addNotification({
        type: 'error',
        title: 'Creation Failed',
        message: errorMessage
      });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.contentContainer}>
        {/* Premium Header */}
        <header className={styles.pageHeader}>
          <div className={styles.headerTitleRow}>
            <div className={styles.headerIcon}>
              <FiTool size={28} />
            </div>
            <div>
              <h1 className={styles.mainTitle}>Register New Service</h1>
              <p className={styles.subTitle}>Create a service record and assign a technician in one seamless step.</p>
            </div>
          </div>
        </header>

        {error && (
          <div className={styles.errorBanner}>
            <div className={styles.errorIcon}>!</div>
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div style={{ padding: '10px', textAlign: 'center', color: '#666' }}>
            Loading data...
          </div>
        )}

        <div className={styles.formContainer}>
          
          {/* Source Toggle */}
          <div className={styles.glassCard}>
            <h2 className={styles.cardTitle}><FiBox /> Source Selection</h2>
            <div className={styles.sourceToggleContainer}>
              <button 
                className={`${styles.sourceToggleBtn} ${formData.source_type === 'manual' ? styles.activeSource : ''}`}
                onClick={() => handleSourceToggle('manual')}
              >
                <span className={styles.radioIndicator}></span>
                Manual Entry
              </button>
              <button 
                className={`${styles.sourceToggleBtn} ${formData.source_type === 'invoice' ? styles.activeSource : ''}`}
                onClick={() => handleSourceToggle('invoice')}
              >
                <span className={styles.radioIndicator}></span>
                Link to Past Invoice
              </button>
            </div>

            {formData.source_type === 'invoice' && (
              <div className={styles.invoiceSearchGrid}>
                <div className={styles.inputGroup}>
                  <label>Select Customer Invoice</label>
                  <div className={styles.searchWrapper}>
                    <FiSearch className={styles.searchIcon} />
                    <select 
                      value={selectedSaleId} 
                      onChange={e => setSelectedSaleId(e.target.value)}
                      className={styles.styledInput}
                    >
                      <option value="">-- Choose an Invoice --</option>
                      {sales.map(s => (
                        <option key={s.id} value={s.id}>{s.bill_number} - {s.customer_name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                
                {selectedSaleId && (
                  <div className={styles.inputGroup}>
                    <label>Select Defective Product</label>
                    <select 
                      value={selectedItemId} 
                      onChange={e => setSelectedItemId(e.target.value)}
                      className={styles.styledInput}
                    >
                      <option value="">-- Choose a Product --</option>
                      {saleItems.map(item => (
                        <option key={item.id} value={item.id}>{item.product_name} (Qty: {item.quantity})</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className={styles.twoColGrid}>
            {/* Customer Details */}
            <div className={styles.glassCard}>
              <h2 className={styles.cardTitle}><FiUser /> Customer Information</h2>
              <div className={styles.formGrid}>
                <div className={styles.inputGroup}>
                  <label>Customer Name <span className={styles.required}>*</span></label>
                  <input 
                    type="text" 
                    value={formData.customer_name} 
                    onChange={e => setFormData({...formData, customer_name: e.target.value})}
                    placeholder="Enter customer name"
                    className={styles.styledInput}
                  />
                </div>
                <div className={styles.inputGroup}>
                  <label>Phone Number</label>
                  <input 
                    type="tel" 
                    value={formData.phone} 
                    onChange={e => setFormData({...formData, phone: e.target.value})}
                    placeholder="Enter phone number"
                    className={styles.styledInput}
                  />
                </div>
              </div>
            </div>

            {/* Machine Details */}
            <div className={styles.glassCard}>
              <h2 className={styles.cardTitle}><FiTool /> Machine Details</h2>
              <div className={styles.formGrid}>
                <div className={styles.inputGroup} style={{ gridColumn: '1 / -1' }}>
                  <label>Machine / Product Name <span className={styles.required}>*</span></label>
                  <input 
                    type="text" 
                    value={formData.product_name} 
                    onChange={e => setFormData({...formData, product_name: e.target.value})}
                    placeholder="e.g. 2HP Submersible Pump"
                    className={styles.styledInput}
                  />
                </div>
                <div className={styles.inputGroup}>
                  <label>Brand</label>
                  <select 
                    value={formData.brand} 
                    onChange={e => setFormData({...formData, brand: e.target.value})}
                    className={styles.styledInput}
                  >
                    <option value="Pond">Pond</option>
                    <option value="SunCraft">SunCraft</option>
                    <option value="Others">Others</option>
                  </select>
                </div>
                {formData.brand === 'Others' && (
                  <div className={styles.inputGroup}>
                    <label>Specify Brand <span className={styles.required}>*</span></label>
                    <input 
                      type="text" 
                      value={formData.custom_brand} 
                      onChange={e => setFormData({...formData, custom_brand: e.target.value})}
                      placeholder="Brand Name"
                      className={styles.styledInput}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Service Configuration & Technician Assignment */}
          <div className={styles.glassCard}>
            <h2 className={styles.cardTitle}><FiCheckCircle /> Workflow & Assignment</h2>
            
            <div className={styles.inputGroup} style={{ marginBottom: '1.5rem' }}>
              <label>Complaint / Issue Description <span className={styles.required}>*</span></label>
              <textarea 
                value={formData.complaint} 
                onChange={e => setFormData({...formData, complaint: e.target.value})}
                placeholder="Describe the customer's reported issue in detail..."
                className={styles.styledTextarea}
                rows="3"
              />
            </div>

            <div className={styles.grid3}>
              <div className={styles.inputGroup}>
                <label>Service Type</label>
                <select 
                  value={formData.service_type} 
                  onChange={e => setFormData({...formData, service_type: e.target.value})}
                  className={styles.styledInput}
                >
                  <option value="Repair">Repair</option>
                  <option value="Maintenance">Maintenance</option>
                  <option value="Installation">Installation</option>
                  <option value="Warranty Claim">Warranty Claim</option>
                </select>
              </div>

              <div className={styles.inputGroup}>
                <label>Service Location</label>
                <select 
                  value={formData.service_location} 
                  onChange={e => setFormData({...formData, service_location: e.target.value})}
                  className={styles.styledInput}
                >
                  <option value="Workshop">In-House Workshop</option>
                  <option value="On-site">On-Site / Field</option>
                </select>
              </div>

              <div className={styles.inputGroup}>
                <label>Receiving Workshop <span className={styles.required}>*</span></label>
                <select 
                  value={formData.workshop_id} 
                  onChange={e => setFormData({...formData, workshop_id: e.target.value})}
                  className={styles.styledInput}
                >
                  <option value="">-- Select Workshop --</option>
                  {warehouses?.map(w => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.assignmentBox}>
              <div className={styles.inputGroup}>
                <label>Assign Technician (Optional but Recommended)</label>
                <p className={styles.helpText}>Select a technician to immediately assign them this job card upon creation.</p>
                <select 
                  value={formData.assigned_to} 
                  onChange={e => setFormData({...formData, assigned_to: e.target.value})}
                  className={styles.styledInput}
                >
                  <option value="">-- Leave Unassigned --</option>
                  {users?.filter(u => u.role === 'TECHNICIAN' || u.role === 'admin').map(u => (
                    <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Service Items */}
          <div className={styles.glassCard}>
            <div className={styles.sectionHeaderFlex}>
              <h2 className={styles.cardTitle} style={{ marginBottom: 0 }}>
                Initial Service Items / Diagnostic Charges
              </h2>
              <button type="button" onClick={handleAddItem} className={styles.addButton}>
                <FiPlus /> Add Item
              </button>
            </div>
            
            <div className={styles.tableWrapper}>
              <table className={styles.itemsTable}>
                <thead>
                  <tr>
                    <th>Item Description <span className={styles.required}>*</span></th>
                    <th>Product SKU (For Inventory)</th>
                    <th style={{width: '90px'}}>Qty <span className={styles.required}>*</span></th>
                    <th style={{width: '120px'}}>Estimated Rate</th>
                    <th style={{width: '120px'}}>Amount</th>
                    <th style={{width: '50px'}}></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={index} className={styles.tableRow}>
                      <td>
                        <input 
                          type="text" 
                          value={item.item_name}
                          onChange={(e) => handleItemChange(index, 'item_name', e.target.value)}
                          placeholder="e.g. Diagnostic Fee"
                          className={styles.tableInput}
                        />
                      </td>
                      <td>
                        <input 
                          type="text" 
                          value={item.product_sku}
                          onChange={(e) => handleItemChange(index, 'product_sku', e.target.value)}
                          placeholder="Optional"
                          className={styles.tableInput}
                        />
                      </td>
                      <td>
                        <input 
                          type="number" 
                          min="1"
                          value={item.qty}
                          onChange={(e) => handleItemChange(index, 'qty', e.target.value)}
                          className={styles.tableInput}
                        />
                      </td>
                      <td>
                        <input 
                          type="number" 
                          min="0"
                          value={item.rate}
                          onChange={(e) => handleItemChange(index, 'rate', e.target.value)}
                          className={styles.tableInput}
                        />
                      </td>
                      <td className={styles.amountCell}>
                        ₹{item.amount.toFixed(2)}
                      </td>
                      <td>
                        <button 
                          type="button" 
                          onClick={() => handleRemoveItem(index)}
                          className={styles.deleteBtn}
                          disabled={items.length === 1}
                        >
                          <FiTrash2 />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={styles.stickyFooter}>
            <button 
              type="button" 
              className={styles.btnSecondary}
              onClick={() => navigate('/services/job-cards')}
              disabled={creating}
            >
              Cancel
            </button>
            <button 
              type="button" 
              className={styles.btnPrimary}
              onClick={handleCreate}
              disabled={creating}
            >
              {creating ? 'Registering Service...' : <><FiSave /> Register Service</>}
            </button>
          </div>
          
        </div>
      </div>
    </div>
  );
}

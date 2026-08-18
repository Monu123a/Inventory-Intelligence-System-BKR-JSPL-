import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useCreateJobCard } from '../../hooks/useServices';
import { useWarehouses, useCreateWarehouse } from '../../hooks/useWarehouses';
import { useUsers, useCreateUser } from '../../hooks/useUsers';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';
import { useAuthStore } from '../../stores/authStore';
import { FiTool, FiPlus, FiTrash2, FiSave, FiX } from 'react-icons/fi';
import AdminPasswordModal from '../../components/common/AdminPasswordModal';
import styles from './JobCardForm.module.css';

const JobCardForm = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const serviceRecordId = searchParams.get('serviceRecordId');
  const companyId = useCompanyStore((state) => state.companyId);
  const { user: currentUser } = useAuthStore();
  const isAdmin = currentUser?.role?.toLowerCase() === 'admin';
  
  const createMutation = useCreateJobCard();
  const { data: warehouses } = useWarehouses();
  const { data: users } = useUsers();
  const createWarehouseMutation = useCreateWarehouse();
  const createUserMutation = useCreateUser();
  
  const [serviceRecord, setServiceRecord] = useState(null);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    workshop_id: '',
    assigned_to: ''
  });
  
  const [items, setItems] = useState([
    { item_name: 'Initial Diagnosis / Service Charge', qty: 1, rate: 0, amount: 0 }
  ]);

  // Modal States
  const [showWorkshopModal, setShowWorkshopModal] = useState(false);
  const [newWorkshopName, setNewWorkshopName] = useState('');
  const [newWorkshopLocation, setNewWorkshopLocation] = useState('');

  const [showTechModal, setShowTechModal] = useState(false);
  const [newTechName, setNewTechName] = useState('');
  const [newTechPhone, setNewTechPhone] = useState('');

  // Password Modal State
  const [passwordModalConfig, setPasswordModalConfig] = useState({
    isOpen: false,
    action: null, // 'workshop' or 'tech'
    actionName: ''
  });

  useEffect(() => {
    if (serviceRecordId) {
      api.get(`/api/services/${serviceRecordId}`).then(res => {
        setServiceRecord(res.data);
      }).catch(err => {
        console.error(err);
        setError('Failed to load Service Record details.');
      });
    }
  }, [serviceRecordId]);

  const handleAddItem = () => {
    setItems([...items, { item_name: '', qty: 1, rate: 0, amount: 0 }]);
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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!serviceRecordId) {
      setError('Missing Service Record ID');
      return;
    }
    if (!formData.workshop_id) {
      setError('Please select a workshop');
      return;
    }
    if (items.length === 0 || !items[0].item_name) {
      setError('Please provide at least one item or service charge');
      return;
    }
    
    setError('');
    const payload = {
      service_record_id: parseInt(serviceRecordId),
      workshop_id: parseInt(formData.workshop_id),
      assigned_to: formData.assigned_to ? parseInt(formData.assigned_to) : null,
      status: 'OPEN',
      items: items.map(item => ({
        ...item,
        qty: parseFloat(item.qty),
        rate: parseFloat(item.rate),
        amount: parseFloat(item.amount),
        source: 'manual'
      }))
    };

    createMutation.mutate(payload, {
      onSuccess: (data) => {
        navigate(`/services/job-cards/${data.id}`);
      },
      onError: (err) => {
        setError(err.response?.data?.detail || 'Failed to create Job Card');
      }
    });
  };

  const handleCreateWorkshop = (adminPassword) => {
    if (!newWorkshopName.trim()) return;
    
    createWarehouseMutation.mutate({
      data: {
        name: newWorkshopName,
        code: 'WS-' + Math.random().toString(36).substr(2, 4).toUpperCase(),
        warehouse_type: 'WORKSHOP',
        status: 'Active',
        address: newWorkshopLocation,
        marketplace: 'N/A',
        external_code: 'N/A'
      },
      adminPassword
    }, {
      onSuccess: (data) => {
        setFormData(prev => ({ ...prev, workshop_id: data.id }));
        setShowWorkshopModal(false);
        setPasswordModalConfig({ isOpen: false, action: null, actionName: '' });
        setNewWorkshopName('');
        setNewWorkshopLocation('');
      },
      onError: () => {
        setPasswordModalConfig({ isOpen: false, action: null, actionName: '' });
      }
    });
  };

  const handleCreateTech = (adminPassword) => {
    if (!newTechName.trim()) return;
    
    createUserMutation.mutate({
      userData: {
        name: newTechName,
        phone: newTechPhone,
        role: 'TECHNICIAN'
      },
      adminPassword
    }, {
      onSuccess: (data) => {
        setFormData(prev => ({ ...prev, assigned_to: data.id }));
        setShowTechModal(false);
        setPasswordModalConfig({ isOpen: false, action: null, actionName: '' });
        setNewTechName('');
        setNewTechPhone('');
      },
      onError: () => {
        setPasswordModalConfig({ isOpen: false, action: null, actionName: '' });
      }
    });
  };

  const handleVerifyPassword = (password) => {
    if (passwordModalConfig.action === 'workshop') {
      handleCreateWorkshop(password);
    } else if (passwordModalConfig.action === 'tech') {
      handleCreateTech(password);
    }
  };

  const triggerWorkshopCreate = (e) => {
    e.preventDefault();
    if (!newWorkshopName.trim()) return;
    setPasswordModalConfig({ isOpen: true, action: 'workshop', actionName: 'create a new workshop' });
  };

  const triggerTechCreate = (e) => {
    e.preventDefault();
    if (!newTechName.trim()) return;
    setPasswordModalConfig({ isOpen: true, action: 'tech', actionName: 'create a new technician' });
  };

  return (
    <div className={styles.pageContainer}>
      <div className={styles.mainWrapper}>
        <div className={styles.headerCard}>
          <h2 className={styles.pageTitle}><FiTool color="#2563eb" /> Create Job Card</h2>
          {serviceRecord ? (
            <p className={styles.pageSubtitle}>For Service Request #{serviceRecord.service_number} • {serviceRecord.customer_name_snapshot}</p>
          ) : (
            <p className={styles.pageSubtitle}>Assign resources and estimate charges</p>
          )}
        </div>
        
        <form onSubmit={handleSubmit} className={styles.formContent}>
          {error && (
            <div className={styles.errorBox}>
              <FiX size={20} />
              <span>{error}</span>
            </div>
          )}

          <div className={styles.grid2}>
            <div className={styles.inputGroup}>
              <div className={styles.labelWrapper}>
                <label className={styles.label}>Assign Workshop <span className={styles.required}>*</span></label>
                {isAdmin && (
                  <button type="button" className={styles.btnAddInline} onClick={() => setShowWorkshopModal(true)}>
                    <FiPlus /> Add Workshop
                  </button>
                )}
              </div>
              <select
                required
                className={styles.input}
                value={formData.workshop_id}
                onChange={e => setFormData({...formData, workshop_id: e.target.value})}
              >
                <option value="">Select Workshop</option>
                {warehouses?.map(w => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
            
            <div className={styles.inputGroup}>
              <div className={styles.labelWrapper}>
                <label className={styles.label}>Assign Technician</label>
                {isAdmin && (
                  <button type="button" className={styles.btnAddInline} onClick={() => setShowTechModal(true)}>
                    <FiPlus /> Add Technician
                  </button>
                )}
              </div>
              <select
                className={styles.input}
                value={formData.assigned_to}
                onChange={e => setFormData({...formData, assigned_to: e.target.value})}
              >
                <option value="">Unassigned</option>
                {users?.map(u => (
                  <option key={u.id} value={u.id}>{u.full_name || u.email || u.username}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>Estimate Items & Services</h3>
              <button type="button" onClick={handleAddItem} className={styles.btnAddItem}>
                <FiPlus /> Add Item
              </button>
            </div>
            
            <div className={styles.itemList}>
              {items.map((item, index) => (
                <div key={index} className={styles.itemRow}>
                  <div className={`${styles.inputGroup} ${styles.itemDesc}`}>
                    <label className={styles.label}>Description</label>
                    <input
                      required
                      type="text"
                      className={styles.input}
                      value={item.item_name}
                      onChange={e => handleItemChange(index, 'item_name', e.target.value)}
                      placeholder="Service charge, spare part..."
                    />
                  </div>
                  <div className={`${styles.inputGroup} ${styles.itemQty}`}>
                    <label className={styles.label}>Qty</label>
                    <input
                      required
                      type="number"
                      min="1"
                      className={styles.input}
                      value={item.qty}
                      onChange={e => handleItemChange(index, 'qty', e.target.value)}
                    />
                  </div>
                  <div className={`${styles.inputGroup} ${styles.itemRate}`}>
                    <label className={styles.label}>Rate (₹)</label>
                    <input
                      required
                      type="number"
                      min="0"
                      step="0.01"
                      className={styles.input}
                      value={item.rate}
                      onChange={e => handleItemChange(index, 'rate', e.target.value)}
                    />
                  </div>
                  <div className={`${styles.inputGroup} ${styles.itemAmount}`}>
                    <label className={styles.label}>Amount</label>
                    <div className={styles.amountBox}>
                      {(item.qty * item.rate).toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(index)}
                      className={styles.btnRemove}
                      disabled={items.length === 1}
                    >
                      <FiTrash2 size={20} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <div className={styles.totalRow}>
              <div className={styles.totalBox}>
                <span className={styles.totalLabel}>Estimated Total</span>
                <div className={styles.totalAmount}>
                  ₹{items.reduce((sum, item) => sum + (item.qty * item.rate), 0).toFixed(2)}
                </div>
              </div>
            </div>
          </div>

          <div className={styles.actionRow}>
            <button
              type="button"
              onClick={() => navigate(serviceRecordId ? `/service/${serviceRecordId}` : '/services/job-cards')}
              className={styles.btnCancel}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isLoading}
              className={styles.btnSubmit}
            >
              {createMutation.isLoading ? 'Creating...' : (
                <><FiSave size={18} /> Generate Job Card</>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Workshop Modal */}
      {showWorkshopModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3>Add Workshop</h3>
              <button type="button" onClick={() => setShowWorkshopModal(false)} className={styles.btnRemove} style={{margin: 0}}><FiX size={20} /></button>
            </div>
            <form onSubmit={triggerWorkshopCreate}>
              <div className={styles.modalBody}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Name <span className={styles.required}>*</span></label>
                  <input required className={styles.input} value={newWorkshopName} onChange={e => setNewWorkshopName(e.target.value)} placeholder="Main Workshop" />
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Location (Optional)</label>
                  <input className={styles.input} value={newWorkshopLocation} onChange={e => setNewWorkshopLocation(e.target.value)} placeholder="City, State" />
                </div>
              </div>
              <div className={styles.modalFooter}>
                <button type="button" onClick={() => setShowWorkshopModal(false)} className={styles.btnCancel}>Cancel</button>
                <button type="submit" disabled={createWarehouseMutation.isLoading} className={styles.btnSubmit}>
                  {createWarehouseMutation.isLoading ? 'Saving...' : 'Save Workshop'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Technician Modal */}
      {showTechModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3>Add Technician</h3>
              <button type="button" onClick={() => setShowTechModal(false)} className={styles.btnRemove} style={{margin: 0}}><FiX size={20} /></button>
            </div>
            <form onSubmit={triggerTechCreate}>
              <div className={styles.modalBody}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Name <span className={styles.required}>*</span></label>
                  <input required className={styles.input} value={newTechName} onChange={e => setNewTechName(e.target.value)} placeholder="John Doe" />
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Phone (Optional)</label>
                  <input className={styles.input} value={newTechPhone} onChange={e => setNewTechPhone(e.target.value)} placeholder="+91 9876543210" />
                </div>
              </div>
              <div className={styles.modalFooter}>
                <button type="button" onClick={() => setShowTechModal(false)} className={styles.btnCancel}>Cancel</button>
                <button type="submit" disabled={createUserMutation.isLoading} className={styles.btnSubmit}>
                  {createUserMutation.isLoading ? 'Saving...' : 'Save Technician'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <AdminPasswordModal 
        isOpen={passwordModalConfig.isOpen}
        onClose={() => setPasswordModalConfig({ isOpen: false, action: null, actionName: '' })}
        onSubmit={handleVerifyPassword}
        actionName={passwordModalConfig.actionName}
      />
    </div>
  );
};

export default JobCardForm;

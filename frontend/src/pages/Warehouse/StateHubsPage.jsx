import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import { Modal } from '../../components/Modal/Modal';
import { FiChevronDown, FiChevronRight, FiMapPin, FiPackage, FiPlus, FiEdit2, FiTrash2 } from 'react-icons/fi';
import { stateHubService } from '../../services/stateHubService';
import { warehouseService } from '../../services/warehouse';
import AdminPasswordModal from '../../components/common/AdminPasswordModal';
import styles from './Warehouse.module.css';

const StateHubsPage = () => {
  const [hubs, setHubs] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [expandedHubs, setExpandedHubs] = useState({});
  const [isHubModalOpen, setIsHubModalOpen] = useState(false);
  const [isWarehouseModalOpen, setIsWarehouseModalOpen] = useState(false);
  const [editingHub, setEditingHub] = useState(null);
  const [editingWarehouse, setEditingWarehouse] = useState(null);
  const [hubFormData, setHubFormData] = useState({ hub_code: '', hub_name: '', state: '', gstin: '', address: '', city: '', state_code: '', contact_person: '', phone: '', email: '' });
  const [warehouseFormData, setWarehouseFormData] = useState({ name: '', code: '', hub_id: '', warehouse_type: 'FULFILLMENT_CENTER', status: 'ACTIVE', external_mappings: [] });
  const [isAssignMode, setIsAssignMode] = useState(false);
  const [selectedUnassignedWhId, setSelectedUnassignedWhId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [pendingActionType, setPendingActionType] = useState(''); // 'warehouse_submit', 'warehouse_delete'


  const fetchData = async () => {
    try {
      setLoading(true);
      const [hubsRes, whRes] = await Promise.all([
        stateHubService.getAll(),
        warehouseService.getWarehouses()
      ]);
      setHubs(hubsRes || []);
      setWarehouses(whRes || []);
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleHub = (hubId) => {
    setExpandedHubs(prev => ({ ...prev, [hubId]: !prev[hubId] }));
  };

  // Hub Modal Handlers
  const handleOpenHubModal = (hub = null) => {
    if (hub) {
      setEditingHub(hub);
      setHubFormData({ 
        hub_code: hub.hub_code || '', 
        hub_name: hub.hub_name || '', 
        state: hub.state || '',
        gstin: hub.gstin || '',
        address: hub.address || '',
        city: hub.city || '',
        state_code: hub.state_code || '',
        contact_person: hub.contact_person || '',
        phone: hub.phone || '',
        email: hub.email || ''
      });
    } else {
      setEditingHub(null);
      setHubFormData({ hub_code: '', hub_name: '', state: '', gstin: '', address: '', city: '', state_code: '', contact_person: '', phone: '', email: '' });
    }
    setIsHubModalOpen(true);
  };

  const handleCloseHubModal = () => {
    setIsHubModalOpen(false);
    setEditingHub(null);
  };

  const handleHubSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingHub) {
        await stateHubService.update(editingHub.id, hubFormData);
      } else {
        await stateHubService.create(hubFormData);
      }
      handleCloseHubModal();
      fetchData();
    } catch (err) {
      alert('Failed to save hub: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteHub = async (id) => {
    if (window.confirm('Are you sure you want to delete this hub?')) {
      try {
        await stateHubService.delete(id);
        fetchData();
      } catch (err) {
        alert('Failed to delete hub');
      }
    }
  };

  // Warehouse Modal Handlers
  const handleOpenWarehouseModal = (hubId = null, wh = null) => {
    setIsAssignMode(false);
    setSelectedUnassignedWhId('');
    if (wh) {
      setEditingWarehouse(wh);
      
      let wType = wh.warehouse_type || 'FULFILLMENT_CENTER';
      if (wType === 'FC') wType = 'FULFILLMENT_CENTER';
      if (wType === 'DC') wType = 'REGIONAL';
      if (wType === 'Store') wType = 'TRANSIT';
      let wStatus = wh.status || 'ACTIVE';
      if (wStatus === 'Active') wStatus = 'ACTIVE';
      if (wStatus === 'Inactive') wStatus = 'INACTIVE';
      setWarehouseFormData({ name: wh.name, code: wh.code, hub_id: wh.hub_id || '', warehouse_type: wType, status: wStatus, external_mappings: wh.external_mappings || [] });

    } else {
      setEditingWarehouse(null);
      setWarehouseFormData({ name: '', code: '', hub_id: hubId || '', warehouse_type: 'FULFILLMENT_CENTER', status: 'ACTIVE', external_mappings: [] });
    }
    setIsWarehouseModalOpen(true);
  };

  const handleCloseWarehouseModal = () => {
    setIsWarehouseModalOpen(false);
    setEditingWarehouse(null);
  };

  
  const handleWarehouseSubmit = (e) => {
    e.preventDefault();
    setPendingActionType('warehouse_submit');
    setIsAdminModalOpen(true);
  };


  
  const handleDeleteWarehouse = (id) => {
    setPendingAction(id);
    setPendingActionType('warehouse_delete');
    setIsAdminModalOpen(true);
  };



  const executeAdminAction = async (password) => {
    try {
      if (pendingActionType === 'warehouse_submit') {
        if (!editingWarehouse && isAssignMode) {
          if (!selectedUnassignedWhId) {
            alert('Please select a warehouse to assign');
            return;
          }
          const existingWh = warehouses.find(w => w.id === parseInt(selectedUnassignedWhId, 10));
          const payload = { ...existingWh, hub_id: parseInt(warehouseFormData.hub_id, 10), admin_password: password };
          await warehouseService.updateWarehouse(existingWh.id, payload);
          handleCloseWarehouseModal();
          fetchData();
          if (payload.hub_id) {
            setExpandedHubs(prev => ({ ...prev, [payload.hub_id]: true }));
          }
        } else {
          const payload = {
            ...warehouseFormData,
            hub_id: warehouseFormData.hub_id ? parseInt(warehouseFormData.hub_id, 10) : null,
            admin_password: password
          };
          if (editingWarehouse) {
            await warehouseService.updateWarehouse(editingWarehouse.id, payload);
          } else {
            await warehouseService.createWarehouse(payload);
          }
          handleCloseWarehouseModal();
          fetchData();
          if (payload.hub_id) {
            setExpandedHubs(prev => ({ ...prev, [payload.hub_id]: true }));
          }
        }
      } else if (pendingActionType === 'warehouse_delete') {
        await warehouseService.deleteWarehouse(pendingAction, password);
        fetchData();
      }
      setIsAdminModalOpen(false);
      setPendingAction(null);
      setPendingActionType('');
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ') : (detail || err.message);
      alert('Action failed: ' + msg);
    }
  };

  return (
    <PageContainer 
      title="Warehouse Hierarchy"
      actions={<Button variant="primary" onClick={() => handleOpenHubModal()}>Add State Hub</Button>}
    >
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <Card>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className={styles.hubList}>
            {hubs.map(hub => {
              const hubWarehouses = warehouses.filter(w => w.hub_id === hub.id);
              const isExpanded = expandedHubs[hub.id];
              return (
                <div key={hub.id} className={styles.hubCard}>
                  <div 
                    className={`${styles.hubHeader} ${isExpanded ? styles.hubHeaderExpanded : ''}`}
                    onClick={() => toggleHub(hub.id)}
                  >
                    <div className={styles.hubHeaderLeft}>
                      <span className={styles.hubIconWrapper}>
                        {isExpanded ? <FiChevronDown /> : <FiChevronRight />}
                      </span>
                      <span className={styles.hubTitle}>
                        <FiMapPin style={{ color: '#3b82f6' }} />
                        {hub.hub_name} ({hub.hub_code})
                      </span>
                      <span className={styles.hubSubtitle}>- {hub.state}</span>
                    </div>
                    <div className={styles.hubHeaderRight} onClick={e => e.stopPropagation()}>
                      <Button variant="secondary" size="small" onClick={() => handleOpenWarehouseModal(hub.id)}>
                        <FiPlus style={{ marginRight: '4px' }} /> FC
                      </Button>
                      <Button variant="secondary" size="small" onClick={() => handleOpenHubModal(hub)}>
                        <FiEdit2 />
                      </Button>
                      <Button variant="danger" size="small" onClick={() => handleDeleteHub(hub.id)}>
                        <FiTrash2 />
                      </Button>
                    </div>
                  </div>
                  
                  {isExpanded && (
                    <div className={styles.hubBody}>
                      {hubWarehouses.length > 0 ? (
                        <div className={styles.warehouseList}>
                          {hubWarehouses.map(wh => (
                            <div key={wh.id} className={styles.warehouseRow}>
                              <div className={styles.warehouseInfo}>
                                <FiPackage className={styles.warehouseIcon} />
                                <span className={styles.warehouseName}>{wh.name}</span>
                                <span className={styles.warehouseCode}>{wh.code}</span>
                                <span style={{ marginLeft: '1rem', fontSize: '0.75rem', backgroundColor: '#e5e7eb', padding: '0.125rem 0.5rem', borderRadius: '1rem' }}>{wh.warehouse_type || 'Unknown'}</span>
                                <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: wh.status === 'Active' ? 'green' : 'gray' }}>{wh.status || 'Active'}</span>
                              </div>
                              <div className={styles.warehouseActions}>
                                <Button variant="secondary" size="small" onClick={() => handleOpenWarehouseModal(hub.id, wh)}>Edit</Button>
                                <Button variant="danger" size="small" onClick={() => handleDeleteWarehouse(wh.id)}>Delete</Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className={styles.emptyState}>No warehouses/FCs found for this hub.</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            {hubs.length === 0 && (
              <p style={{ textAlign: 'center', color: '#6b7280', padding: '2rem' }}>No state hubs found. Add one to get started.</p>
            )}
          </div>
        )}
      </Card>

      {/* Hub Modal */}
      <Modal isOpen={isHubModalOpen} onClose={handleCloseHubModal} title={editingHub ? 'Edit State Hub' : 'Add State Hub'}>
        <form onSubmit={handleHubSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input label="Hub Code *" value={hubFormData.hub_code} onChange={(e) => setHubFormData({ ...hubFormData, hub_code: e.target.value })} required />
            <Input label="Legal Hub Name *" value={hubFormData.hub_name} onChange={(e) => setHubFormData({ ...hubFormData, hub_name: e.target.value })} required />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input label="GSTIN *" value={hubFormData.gstin} onChange={(e) => setHubFormData({ ...hubFormData, gstin: e.target.value })} required />
            <Input label="Contact Person" value={hubFormData.contact_person} onChange={(e) => setHubFormData({ ...hubFormData, contact_person: e.target.value })} />
          </div>
          <Input label="Billing Address *" value={hubFormData.address} onChange={(e) => setHubFormData({ ...hubFormData, address: e.target.value })} required />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <Input label="City" value={hubFormData.city} onChange={(e) => setHubFormData({ ...hubFormData, city: e.target.value })} />
            <Input label="State *" value={hubFormData.state} onChange={(e) => setHubFormData({ ...hubFormData, state: e.target.value })} required />
            <Input label="State Code" value={hubFormData.state_code} onChange={(e) => setHubFormData({ ...hubFormData, state_code: e.target.value })} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input label="Phone" value={hubFormData.phone} onChange={(e) => setHubFormData({ ...hubFormData, phone: e.target.value })} />
            <Input label="Email" value={hubFormData.email} onChange={(e) => setHubFormData({ ...hubFormData, email: e.target.value })} type="email" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            <Button type="button" variant="secondary" onClick={handleCloseHubModal}>Cancel</Button>
            <Button type="submit" variant="primary">Save</Button>
          </div>
        </form>
      </Modal>

      {/* Warehouse Modal */}
      <Modal isOpen={isWarehouseModalOpen} onClose={handleCloseWarehouseModal} title={editingWarehouse ? 'Edit Warehouse / FC' : 'Add Warehouse / FC'}>
        <form onSubmit={handleWarehouseSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {!editingWarehouse && (
            <div style={{ display: 'flex', gap: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e5e7eb' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="radio" checked={!isAssignMode} onChange={() => setIsAssignMode(false)} /> 
                Create New
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="radio" checked={isAssignMode} onChange={() => setIsAssignMode(true)} /> 
                Assign Existing
              </label>
            </div>
          )}

          {!editingWarehouse && isAssignMode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Select Unassigned Warehouse</label>
              <select 
                value={selectedUnassignedWhId} 
                onChange={(e) => setSelectedUnassignedWhId(e.target.value)}
                style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
                required
              >
                <option value="">Select a warehouse...</option>
                {warehouses.filter(w => !w.hub_id).map(w => (
                  <option key={w.id} value={w.id}>{w.name} ({w.code})</option>
                ))}
              </select>
            </div>
          ) : (
            <>
              <Input label="Warehouse Name" value={warehouseFormData.name} onChange={(e) => setWarehouseFormData({ ...warehouseFormData, name: e.target.value })} required />
              <Input label="Warehouse Code" value={warehouseFormData.code} onChange={(e) => setWarehouseFormData({ ...warehouseFormData, code: e.target.value })} required />
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Warehouse Type</label>
                <select 
                  value={warehouseFormData.warehouse_type} 
                  onChange={(e) => setWarehouseFormData({ ...warehouseFormData, warehouse_type: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
                >
                  <option value="FULFILLMENT_CENTER">Fulfillment Center</option>
                  <option value="CENTRAL">Central Warehouse</option>
                  <option value="REGIONAL">Regional Distribution Center</option>
                  <option value="TRANSIT">Transit Node</option>
                </select>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Status</label>
                <select 
                  value={warehouseFormData.status} 
                  onChange={(e) => setWarehouseFormData({ ...warehouseFormData, status: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
                >
                  <option value="ACTIVE">Active</option>
                  <option value="INACTIVE">Inactive</option>
                  <option value="UNDER_MAINTENANCE">Under Maintenance</option>
                  <option value="BLOCKED">Blocked</option>
                </select>
              </div>

              <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '1rem', marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>External Mappings</label>
                  <Button type="button" variant="secondary" size="small" onClick={() => setWarehouseFormData({ ...warehouseFormData, external_mappings: [...warehouseFormData.external_mappings, { marketplace: '', external_code: '' }] })}>
                    <FiPlus /> Add
                  </Button>
                </div>
                {warehouseFormData.external_mappings.map((mapping, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
                    <Input placeholder="Marketplace (e.g. Amazon)" value={mapping.marketplace} onChange={(e) => {
                      const newMappings = [...warehouseFormData.external_mappings];
                      newMappings[idx].marketplace = e.target.value;
                      setWarehouseFormData({ ...warehouseFormData, external_mappings: newMappings });
                    }} />
                    <Input placeholder="External Code" value={mapping.external_code} onChange={(e) => {
                      const newMappings = [...warehouseFormData.external_mappings];
                      newMappings[idx].external_code = e.target.value;
                      setWarehouseFormData({ ...warehouseFormData, external_mappings: newMappings });
                    }} />
                    <Button type="button" variant="danger" size="small" onClick={() => {
                      const newMappings = warehouseFormData.external_mappings.filter((_, i) => i !== idx);
                      setWarehouseFormData({ ...warehouseFormData, external_mappings: newMappings });
                    }}>
                      <FiTrash2 />
                    </Button>
                  </div>
                ))}
              </div>
            </>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Assigned Hub</label>
            <select 
              value={warehouseFormData.hub_id} 
              onChange={(e) => setWarehouseFormData({ ...warehouseFormData, hub_id: e.target.value })}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
              required
            >
              <option value="">Select a Hub</option>
              {hubs.map(hub => (
                <option key={hub.id} value={hub.id}>{hub.hub_name}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            <Button type="button" variant="secondary" onClick={handleCloseWarehouseModal}>Cancel</Button>
            <Button type="submit" variant="primary">Save</Button>
          </div>
        </form>
      </Modal>
    
      <AdminPasswordModal
        isOpen={isAdminModalOpen}
        onClose={() => {
          setIsAdminModalOpen(false);
          setPendingAction(null);
          setPendingActionType('');
        }}
        onSubmit={executeAdminAction}
        actionName={pendingActionType === 'warehouse_delete' ? 'Delete Warehouse' : 'Save Warehouse'}
      />

    </PageContainer>
  );
};

export default StateHubsPage;

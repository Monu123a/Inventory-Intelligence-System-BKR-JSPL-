import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import { Modal } from '../../components/Modal/Modal';
import api from '../../services/api';

const WarehousesPage = () => {
  const [warehouses, setWarehouses] = useState([]);
  const [hubs, setHubs] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState(null);
  const [formData, setFormData] = useState({ name: '', code: '', hub_id: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchWarehouses = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/warehouses');
      setWarehouses(response.data || []);
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to load warehouses');
    } finally {
      setLoading(false);
    }
  };

  const fetchHubs = async () => {
    try {
      const response = await api.get('/api/state-hubs');
      setHubs(response.data || []);
    } catch (err) {
      console.error('Failed to load hubs', err);
    }
  };

  useEffect(() => {
    fetchWarehouses();
    fetchHubs();
  }, []);

  const handleOpenModal = (wh = null) => {
    if (wh) {
      setEditingWarehouse(wh);
      setFormData({ name: wh.name, code: wh.code, hub_id: wh.hub_id || '' });
    } else {
      setEditingWarehouse(null);
      setFormData({ name: '', code: '', hub_id: '' });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingWarehouse(null);
    setFormData({ name: '', code: '', hub_id: '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        hub_id: formData.hub_id ? parseInt(formData.hub_id, 10) : null
      };
      
      if (editingWarehouse) {
        await api.put(`/api/warehouses/${editingWarehouse.id}`, payload);
      } else {
        await api.post('/api/warehouses', payload);
      }
      handleCloseModal();
      fetchWarehouses();
    } catch (err) {
      console.error(err);
      alert('Failed to save warehouse: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this warehouse?')) {
      try {
        await api.delete(`/api/warehouses/${id}`);
        fetchWarehouses();
      } catch (err) {
        console.error(err);
        alert('Failed to delete warehouse');
      }
    }
  };

  const getHubName = (hubId) => {
    const hub = hubs.find(h => h.id === hubId);
    return hub ? hub.hub_name : 'Unassigned';
  };

  return (
    <PageContainer 
      title="Master Warehouses"
      actions={<Button variant="primary" onClick={() => handleOpenModal()}>Add Warehouse</Button>}
    >
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <Card>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table style={{ width: '100%', textAlign: 'left' }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Code</th>
                <th>Assigned Hub</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {warehouses.map(wh => (
                <tr key={wh.id}>
                  <td>{wh.id}</td>
                  <td>{wh.name}</td>
                  <td>{wh.code}</td>
                  <td>{wh.hub || getHubName(wh.hub_id)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <Link 
                        to={`/warehouse/${wh.id}`} 
                        style={{ 
                          textDecoration: 'none', 
                          color: '#3b82f6', 
                          fontWeight: '600', 
                          fontSize: '0.875rem',
                          padding: '0.375rem 0.75rem', 
                          borderRadius: '999px', 
                          backgroundColor: '#eff6ff',
                          transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.backgroundColor = '#dbeafe'}
                        onMouseOut={(e) => e.target.style.backgroundColor = '#eff6ff'}
                      >
                        Details
                      </Link>
                      <Link 
                        to={`/warehouse/${wh.id}/users`} 
                        style={{ 
                          textDecoration: 'none', 
                          color: '#8b5cf6', 
                          fontWeight: '600', 
                          fontSize: '0.875rem',
                          padding: '0.375rem 0.75rem', 
                          borderRadius: '999px', 
                          backgroundColor: '#f5f3ff',
                          transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.target.style.backgroundColor = '#ede9fe'}
                        onMouseOut={(e) => e.target.style.backgroundColor = '#f5f3ff'}
                      >
                        Users
                      </Link>
                      <Button variant="secondary" size="small" onClick={() => handleOpenModal(wh)}>Edit</Button>
                      <Button variant="danger" size="small" onClick={() => handleDelete(wh.id)}>Delete</Button>
                    </div>
                  </td>
                </tr>
              ))}
              {warehouses.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center' }}>No warehouses found</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <Modal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
        title={editingWarehouse ? 'Edit Warehouse' : 'Add Warehouse'}
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input 
            label="Warehouse Name" 
            value={formData.name} 
            onChange={(e) => setFormData({ ...formData, name: e.target.value })} 
            required 
          />
          <Input 
            label="Warehouse Code" 
            value={formData.code} 
            onChange={(e) => setFormData({ ...formData, code: e.target.value })} 
            required 
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Assigned Hub</label>
            <select 
              value={formData.hub_id} 
              onChange={(e) => setFormData({ ...formData, hub_id: e.target.value })}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
            >
              <option value="">Select a Hub (Optional)</option>
              {hubs.map(hub => (
                <option key={hub.id} value={hub.id}>{hub.hub_name}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            <Button type="button" variant="secondary" onClick={handleCloseModal}>Cancel</Button>
            <Button type="submit" variant="primary">Save</Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
};

export default WarehousesPage;

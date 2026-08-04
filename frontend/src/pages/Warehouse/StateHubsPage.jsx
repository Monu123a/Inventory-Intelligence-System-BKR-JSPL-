import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import { Modal } from '../../components/Modal/Modal';
import api from '../../services/api';

const StateHubsPage = () => {
  const [hubs, setHubs] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingHub, setEditingHub] = useState(null);
  const [formData, setFormData] = useState({ hub_code: '', hub_name: '', state: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchHubs = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/state-hubs');
      setHubs(response.data || []);
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to load state hubs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHubs();
  }, []);

  const handleOpenModal = (hub = null) => {
    if (hub) {
      setEditingHub(hub);
      setFormData({ hub_code: hub.hub_code || '', hub_name: hub.hub_name || '', state: hub.state || '' });
    } else {
      setEditingHub(null);
      setFormData({ hub_code: '', hub_name: '', state: '' });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingHub(null);
    setFormData({ hub_code: '', hub_name: '', state: '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingHub) {
        await api.put(`/api/state-hubs/${editingHub.id}`, formData);
      } else {
        await api.post('/api/state-hubs', formData);
      }
      handleCloseModal();
      fetchHubs();
    } catch (err) {
      console.error(err);
      alert('Failed to save hub: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this hub?')) {
      try {
        await api.delete(`/api/state-hubs/${id}`);
        fetchHubs();
      } catch (err) {
        console.error(err);
        alert('Failed to delete hub');
      }
    }
  };

  return (
    <PageContainer 
      title="State Hubs"
      actions={<Button variant="primary" onClick={() => handleOpenModal()}>Add Hub</Button>}
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
                <th>Hub Code</th>
                <th>Hub Name</th>
                <th>State</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {hubs.map(hub => (
                <tr key={hub.id}>
                  <td>{hub.id}</td>
                  <td>{hub.hub_code}</td>
                  <td>{hub.hub_name}</td>
                  <td>{hub.state}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <Button variant="secondary" size="small" onClick={() => handleOpenModal(hub)}>Edit</Button>
                      <Button variant="danger" size="small" onClick={() => handleDelete(hub.id)}>Delete</Button>
                    </div>
                  </td>
                </tr>
              ))}
              {hubs.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center' }}>No state hubs found</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <Modal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
        title={editingHub ? 'Edit Hub' : 'Add Hub'}
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input 
            label="Hub Code" 
            value={formData.hub_code} 
            onChange={(e) => setFormData({ ...formData, hub_code: e.target.value })} 
            required 
          />
          <Input 
            label="Hub Name" 
            value={formData.hub_name} 
            onChange={(e) => setFormData({ ...formData, hub_name: e.target.value })} 
            required 
          />
          <Input 
            label="State" 
            value={formData.state} 
            onChange={(e) => setFormData({ ...formData, state: e.target.value })} 
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            <Button type="button" variant="secondary" onClick={handleCloseModal}>Cancel</Button>
            <Button type="submit" variant="primary">Save</Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
};

export default StateHubsPage;

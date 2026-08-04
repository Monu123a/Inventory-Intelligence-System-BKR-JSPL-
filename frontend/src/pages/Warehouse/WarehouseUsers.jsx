import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import { Modal } from '../../components/Modal/Modal';
import api from '../../services/api';

const WarehouseUsers = () => {
  const { id } = useParams();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ user_id: '', permission: 'VIEW' });
  const [allUsers, setAllUsers] = useState([]); // For assignment dropdown

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/warehouses/${id}/users`);
      setUsers(response.data || []);
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to load users for this warehouse');
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    try {
      const response = await api.get('/api/users'); // Assuming this endpoint exists
      setAllUsers(response.data || []);
    } catch (err) {
      console.error('Could not load user list for assignment', err);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchAllUsers();
  }, [id]);

  const handleOpenModal = () => {
    setFormData({ user_id: '', permission: 'VIEW' });
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setFormData({ user_id: '', permission: 'VIEW' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        user_id: parseInt(formData.user_id, 10),
        permission: formData.permission
      };
      await api.post(`/api/warehouses/${id}/users`, payload);
      handleCloseModal();
      fetchUsers();
    } catch (err) {
      console.error(err);
      alert('Failed to assign user');
    }
  };

  const handleRemoveUser = async (userId) => {
    if (window.confirm('Are you sure you want to remove this user from the warehouse?')) {
      try {
        await api.delete(`/api/warehouses/${id}/users/${userId}`);
        fetchUsers();
      } catch (err) {
        console.error(err);
        alert('Failed to remove user');
      }
    }
  };

  return (
    <PageContainer 
      title={`Manage Users - Warehouse ${id}`}
      actions={<Button variant="primary" onClick={handleOpenModal}>Assign User</Button>}
    >
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <Card>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table style={{ width: '100%', textAlign: 'left' }}>
            <thead>
              <tr>
                <th>User ID/Name</th>
                <th>Permission</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>{user.name || user.user_id || user.id}</td>
                  <td>{user.role}</td>
                  <td>
                    <Button variant="danger" size="small" onClick={() => handleRemoveUser(user.id)}>Remove</Button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="3" style={{ textAlign: 'center' }}>No users assigned</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <Modal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
        title="Assign User"
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>User</label>
            <select 
              value={formData.user_id} 
              onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
              required
            >
              <option value="">Select a user</option>
              {allUsers.map(u => (
                <option key={u.id} value={u.id}>{u.name || u.email || u.id}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Role</label>
            <select 
              value={formData.permission} 
              onChange={(e) => setFormData({ ...formData, permission: e.target.value })}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
            >
              <option value="VIEW">VIEW</option>
              <option value="MANAGE">MANAGE</option>
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

export default WarehouseUsers;

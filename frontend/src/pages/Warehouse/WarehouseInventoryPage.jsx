import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { SearchBar } from '../../components/forms/SearchBar';
import api from '../../services/api';

const WarehouseInventoryPage = () => {
  const [inventory, setInventory] = useState([]);
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchInventory = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/warehouse-inventory');
        setInventory(response.data || []);
        setError('');
      } catch (err) {
        console.error(err);
        setError('Failed to load inventory');
        setInventory([]);
      } finally {
        setLoading(false);
      }
    };
    fetchInventory();
  }, []);

  const filteredInventory = inventory.filter(item => !category || item.category === category);

  return (
    <PageContainer title="Warehouse Inventory">
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <Card>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <SearchBar placeholder="Search SKU..." />
          <select 
            value={category} 
            onChange={e => setCategory(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db' }}
          >
            <option value="">All Categories</option>
            <option value="Electronics">Electronics</option>
            <option value="Apparel">Apparel</option>
          </select>
        </div>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table style={{ width: '100%', textAlign: 'left' }}>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Name</th>
                <th>Category</th>
                <th>Quantity</th>
              </tr>
            </thead>
            <tbody>
              {filteredInventory.map(item => (
                <tr key={item.id}>
                  <td>{item.sku}</td>
                  <td>{item.name}</td>
                  <td>{item.category}</td>
                  <td>{item.quantity}</td>
                </tr>
              ))}
              {filteredInventory.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center' }}>No inventory items found</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>
    </PageContainer>
  );
};

export default WarehouseInventoryPage;

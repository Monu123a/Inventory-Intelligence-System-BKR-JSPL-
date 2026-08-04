import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import api from '../../services/api';

const WarehouseDetailPage = () => {
  const { id } = useParams();
  const [warehouse, setWarehouse] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true);
        // Assuming there is an endpoint to get single warehouse details
        const whResponse = await api.get(`/api/warehouses/${id}`);
        setWarehouse(whResponse.data);

        // Fetch inventory to calculate summary
        const invResponse = await api.get('/api/warehouse-inventory');
        setInventory(invResponse.data || []);
        setError('');
      } catch (err) {
        console.error(err);
        setError('Failed to load warehouse details');
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [id]);

  if (loading) {
    return <PageContainer title={`Warehouse Details - ${id}`}><p>Loading...</p></PageContainer>;
  }

  if (error) {
    return <PageContainer title={`Warehouse Details - ${id}`}><p style={{ color: 'red' }}>{error}</p></PageContainer>;
  }

  if (!warehouse) {
    return <PageContainer title={`Warehouse Details - ${id}`}><p>Warehouse not found.</p></PageContainer>;
  }

  // Calculate summary based on this warehouse's inventory if the API provided a way to filter by warehouse ID.
  // For now we assume the inventory endpoint returns all inventory or we can filter it (if warehouse_id is in item).
  const warehouseInventory = inventory.filter(item => item.warehouse_id === Number(id) || !item.warehouse_id);
  const totalItems = warehouseInventory.reduce((acc, item) => acc + (item.quantity || 0), 0);
  const lowStock = warehouseInventory.filter(item => item.quantity < 10).length;
  const value = warehouseInventory.reduce((acc, item) => acc + (item.price || 0) * (item.quantity || 0), 0);

  return (
    <PageContainer title={`Warehouse Details - ${warehouse.name || id}`}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <Card>
          <h3>Information</h3>
          <p><strong>Name:</strong> {warehouse.name}</p>
          <p><strong>Code:</strong> {warehouse.code}</p>
          <p><strong>Location/Hub:</strong> {warehouse.hub || warehouse.hub_id || 'N/A'}</p>
        </Card>
        <Card>
          <h3>Inventory Summary</h3>
          <p><strong>Total Items:</strong> {totalItems}</p>
          <p><strong>Low Stock:</strong> {lowStock}</p>
          <p><strong>Value:</strong> ${value.toFixed(2)}</p>
        </Card>
      </div>
    </PageContainer>
  );
};

export default WarehouseDetailPage;

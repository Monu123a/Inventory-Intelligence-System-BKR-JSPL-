import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { SearchBar } from '../../components/forms/SearchBar';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import Button from '../../components/forms/Button';
import { FiArrowLeft, FiPackage, FiMapPin, FiBox } from 'react-icons/fi';
import api from '../../services/api';
import styles from './Warehouse.module.css';

const WarehouseInventoryPage = () => {
  const [warehouses, setWarehouses] = useState([]);
  const [hubs, setHubs] = useState({});
  const [selectedWarehouse, setSelectedWarehouse] = useState(null);
  
  const [inventory, setInventory] = useState([]);
  const [skuSearch, setSkuSearch] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch warehouses on mount
  useEffect(() => {
    const fetchWarehouses = async () => {
      try {
        setLoading(true);
        const [whRes, hubsRes] = await Promise.all([
          api.get('/api/warehouses'),
          api.get('/api/state-hubs')
        ]);
        const hubMap = {};
        if (hubsRes.data) {
          hubsRes.data.forEach(h => {
            hubMap[h.id] = h;
          });
        }
        setHubs(hubMap);
        setWarehouses(whRes.data || []);
      } catch (err) {
        setError('Failed to load warehouses');
      } finally {
        setLoading(false);
      }
    };
    if (!selectedWarehouse) {
      fetchWarehouses();
    }
  }, [selectedWarehouse]);

  // Fetch inventory when a warehouse is selected
  useEffect(() => {
    if (selectedWarehouse) {
      const fetchInventory = async () => {
        try {
          setLoading(true);
          const response = await api.get(`/api/warehouse-inventory?warehouse_id=${selectedWarehouse.id}`);
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
    }
  }, [selectedWarehouse]);

  // Handle warehouse selection
  if (!selectedWarehouse) {
    return (
      <PageContainer title="Select Warehouse / FC">
        {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
        <Card noPadding>
          <div className={styles.toolbar}>
            <p style={{ margin: 0, color: '#4b5563', fontWeight: '500' }}>
              Select a warehouse to view its current inventory levels.
            </p>
          </div>
          <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {loading ? (
              <p>Loading warehouses...</p>
            ) : warehouses.length === 0 ? (
              <p className={styles.emptyState}>No warehouses found. Please create one in State Hubs.</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
                {warehouses.map(wh => {
                  const hub = hubs[wh.hub_id] || {};
                  return (
                    <div key={wh.id} style={{ 
                      border: '1px solid #e5e7eb', 
                      borderRadius: '8px', 
                      padding: '1.5rem',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      backgroundColor: '#fff',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
                    }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                          <FiPackage style={{ color: '#3b82f6', fontSize: '1.25rem' }} />
                          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#111827' }}>{wh.name}</h3>
                          <span className={styles.warehouseCode}>{wh.code}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#6b7280', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                          <FiMapPin />
                          <span>Hub: {hub.hub_name || 'Unassigned'} {hub.state ? `(${hub.state})` : ''}</span>
                        </div>
                      </div>
                      <Button variant="primary" onClick={() => setSelectedWarehouse(wh)} style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center' }}>
                        <FiBox /> View Inventory
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Card>
      </PageContainer>
    );
  }

  // Handle Inventory View for selected warehouse
  const columns = [
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: 'Product Name' },
    { key: 'category', label: 'Category' },
    { key: 'quantity', label: 'Total Qty' },
    { key: 'available_qty', label: 'Available Qty' },
    { key: 'reserved_qty', label: 'Reserved Qty' },
  ];

  const filteredInventory = inventory.filter(item => {
    const matchCategory = !category || item.category === category;
    const matchSearch = !skuSearch || (item.sku && item.sku.toLowerCase().includes(skuSearch.toLowerCase())) || (item.name && item.name.toLowerCase().includes(skuSearch.toLowerCase()));
    return matchCategory && matchSearch;
  });

  return (
    <PageContainer 
      title={`Inventory: ${selectedWarehouse.name} (${selectedWarehouse.code})`}
      actions={
        <Button variant="secondary" onClick={() => setSelectedWarehouse(null)}>
          <FiArrowLeft style={{ marginRight: '8px' }} /> Back to Warehouses
        </Button>
      }
    >
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <Card noPadding>
        <div className={styles.toolbar}>
          <div style={{ display: 'flex', gap: '1rem', flex: 1 }}>
            <div style={{ maxWidth: '300px', width: '100%' }}>
              <SearchBar 
                placeholder="Search SKU or Name..." 
                value={skuSearch}
                onSearch={setSkuSearch}
              />
            </div>
            <select 
              value={category} 
              onChange={e => setCategory(e.target.value)}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #d1d5db', backgroundColor: '#fff' }}
            >
              <option value="">All Categories</option>
              <option value="Electronics">Electronics</option>
              <option value="Apparel">Apparel</option>
              <option value="Home">Home</option>
            </select>
          </div>
        </div>
        
        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading inventory...</td></tr>
              ) : filteredInventory.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    No inventory found in this warehouse matching your filters.
                  </td>
                </tr>
              ) : (
                filteredInventory.map(item => (
                  <TableRow key={item.id} row={item} columns={columns} />
                ))
              )}
            </tbody>
          </DataTable>
        </div>
      </Card>
    </PageContainer>
  );
};

export default WarehouseInventoryPage;

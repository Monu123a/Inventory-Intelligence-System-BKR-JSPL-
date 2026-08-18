import React, { useState, useEffect } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../components/DataTable';
import { SearchBar } from '../../components/forms/SearchBar';
import { stateHubService } from '../../services/stateHubService';
import { warehouseService } from '../../services/warehouse';
import styles from './Warehouse.module.css';

const WarehouseMasterList = () => {
  const [warehouses, setWarehouses] = useState([]);
  const [hubs, setHubs] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [whData, hubData] = await Promise.all([
          warehouseService.getWarehouses(),
          stateHubService.getAll()
        ]);
        
        // Map hubs for quick lookup
        const hubMap = {};
        if (hubData) {
          hubData.forEach(h => {
            hubMap[h.id] = h;
          });
        }
        setHubs(hubMap);
        setWarehouses(whData || []);
      } catch (err) {
        setError('Failed to load warehouses');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const columns = [
    { key: 'code', label: 'Warehouse Code' },
    { key: 'name', label: 'Warehouse / FC Name' },
    { key: 'warehouse_type', label: 'Type' },
    { key: 'status', label: 'Status' },
    { key: 'hub_name', label: 'State Hub' },
    { key: 'state', label: 'State' },
  ];

  const filteredWarehouses = warehouses.filter(wh => {
    if (!search) return true;
    const s = search.toLowerCase();
    const hub = hubs[wh.hub_id] || {};
    return (
      (wh.name && wh.name.toLowerCase().includes(s)) ||
      (wh.code && wh.code.toLowerCase().includes(s)) ||
      (hub.hub_name && hub.hub_name.toLowerCase().includes(s))
    );
  }).map(wh => {
    const hub = hubs[wh.hub_id] || {};
    return {
      ...wh,
      hub_name: hub.hub_name || (
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Unassigned
          <span style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: '500' }}>Migration Required</span>
        </span>
      ),
      state: hub.state || '-',
      warehouse_type: wh.warehouse_type || '-',
      status: wh.status || 'Active'
    };
  });

  return (
    <PageContainer title="All Warehouses / FCs">
      <Card noPadding>
        <div className={styles.toolbar}>
          <SearchBar 
            onSearch={setSearch} 
            placeholder="Search by warehouse name, code, or hub..." 
            value={search}
          />
        </div>
        <div className={styles.tableWrapper}>
          <DataTable>
            <TableHeader columns={columns} />
            <tbody>
              {loading ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>Loading warehouses...</td></tr>
              ) : error ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem', color: 'red' }}>{error}</td></tr>
              ) : filteredWarehouses.length === 0 ? (
                <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: '2rem' }}>No warehouses found.</td></tr>
              ) : (
                filteredWarehouses.map((wh) => (
                  <TableRow key={wh.id} row={wh} columns={columns} />
                ))
              )}
            </tbody>
          </DataTable>
        </div>
      </Card>
    </PageContainer>
  );
};

export default WarehouseMasterList;

import React from 'react';
import { useWarehouses } from '../../../hooks/useWarehouses';
import { FiMapPin, FiBox, FiTrendingUp, FiServer } from 'react-icons/fi';
import styles from '../Overview.module.css';

export const WarehouseHierarchy = () => {
  const { data: warehouses, isPending } = useWarehouses({ limit: 100 });

  if (isPending) {
    return <div className={styles.skeletonCard} style={{ height: '200px' }} />;
  }

  const whList = warehouses || [];

  // Group by Hub
  const hubMap = {};
  whList.forEach(wh => {
    // Attempt to identify hub name, defaulting if not found
    const hubName = wh.hub?.name || wh.hub_name || wh.state || 'Unassigned Hub';
    if (!hubMap[hubName]) {
      hubMap[hubName] = {
        name: hubName,
        fcs: [],
        totalInventory: 0,
        totalProducts: 0
      };
    }
    
    // Check if it's an FC
    if (wh.warehouse_type === 'FULFILLMENT_CENTER' || wh.code?.includes('FC') || true) {
      hubMap[hubName].fcs.push(wh);
    }
    
    hubMap[hubName].totalInventory += (wh.total_inventory || 0);
    hubMap[hubName].totalProducts += (wh.total_products || 0);
  });

  const hubs = Object.values(hubMap).sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div style={{ backgroundColor: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
      <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#111827', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <FiMapPin style={{ color: '#3b82f6' }} />
        Warehouse Network: State Hubs &rarr; FCs
      </h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {hubs.length === 0 ? (
          <p style={{ color: '#6b7280', fontSize: '14px' }}>No warehouses found.</p>
        ) : (
          hubs.map((hub, idx) => (
            <div key={idx} style={{ border: '1px solid #e5e7eb', borderRadius: '8px', overflow: 'hidden' }}>
              
              <div style={{ backgroundColor: '#f9fafb', padding: '12px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FiServer style={{ color: '#4b5563' }} />
                  <span style={{ fontWeight: 600, color: '#374151' }}>{hub.name}</span>
                  <span style={{ fontSize: '12px', padding: '2px 8px', backgroundColor: '#dbeafe', color: '#1d4ed8', borderRadius: '12px', fontWeight: 500 }}>
                    {hub.fcs.length} FCs
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#4b5563' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FiBox /> {hub.totalProducts.toLocaleString()} Products
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FiTrendingUp /> {hub.totalInventory.toLocaleString()} Units
                  </span>
                </div>
              </div>

              <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
                {hub.fcs.map(fc => (
                  <div key={fc.id} style={{ padding: '12px', border: '1px solid #f3f4f6', borderRadius: '6px', backgroundColor: '#fff', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
                    <div style={{ fontWeight: 500, color: '#111827', fontSize: '14px', marginBottom: '4px' }}>{fc.name}</div>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>Code: {fc.code}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                      <span style={{ color: '#4b5563' }}>Stock: <strong style={{ color: '#111827' }}>{fc.total_inventory || 0}</strong></span>
                      <span style={{ color: '#4b5563' }}>Products: <strong style={{ color: '#111827' }}>{fc.total_products || 0}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
              
            </div>
          ))
        )}
      </div>
    </div>
  );
};

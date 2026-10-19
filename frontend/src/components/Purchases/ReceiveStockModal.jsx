import React, { useState, useEffect } from 'react';
import { Modal } from '../Modal/Modal';
import api from '../../services/api';
import { PurchaseService } from '../../services/purchaseService';

export const ReceiveStockModal = ({ isOpen, onClose, purchase, onSuccess }) => {
  const [warehouses, setWarehouses] = useState([]);
  const [warehouseId, setWarehouseId] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.get('/api/warehouses/').then(res => {
        setWarehouses(res.data);
        if (purchase?.warehouse_id) {
          setWarehouseId(String(purchase.warehouse_id));
        } else if (res.data.length > 0) {
          const defaultWh = res.data.find(w => w.name.toLowerCase().includes('central') || w.name.toLowerCase().includes('bkr')) || res.data[0];
          setWarehouseId(String(defaultWh.id));
        }
      }).catch(console.error);
    }
  }, [isOpen, purchase]);

  if (!purchase) return null;

  const handleReceive = async (e) => {
    e.preventDefault();
    if (!warehouseId) {
      alert("Please select a destination warehouse.");
      return;
    }
    setLoading(true);
    try {
      const res = await PurchaseService.receivePurchase(purchase.id, {
        idempotency_key: `recv-${crypto.randomUUID()}`,
        warehouse_id: parseInt(warehouseId)
      });
      alert(`Stock received successfully! Added ${res.movements || ''} inventory movements into selected warehouse.`);
      onSuccess();
      onClose();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        alert(detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n'));
      } else {
        alert(detail || err.message || "Error receiving purchase stock");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Receive Stock - ${purchase.invoice_number || purchase.id}`}>
      <form onSubmit={handleReceive}>
        <div style={{ marginBottom: '15px' }}>
          <p style={{ margin: '0 0 6px 0', fontSize: '14px', color: '#475569' }}>
            <strong>Vendor:</strong> {purchase.vendor_name || 'N/A'}
          </p>
          <p style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#475569' }}>
            <strong>Bill Total:</strong> ₹ {Number(purchase.total_amount || 0).toFixed(2)}
          </p>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
            Destination Warehouse (Stock will be added ONLY here) *
          </label>
          <select 
            value={warehouseId} 
            onChange={e => setWarehouseId(e.target.value)} 
            required
            style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none' }}
          >
            <option value="">-- Select Warehouse --</option>
            {warehouses.map(w => (
              <option key={w.id} value={w.id}>{w.name} ({w.code})</option>
            ))}
          </select>
        </div>

        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px', padding: '10px 12px', marginBottom: '20px', fontSize: '13px', color: '#166534' }}>
          ✓ Inventory for all items in this bill will be increased exclusively in the selected destination warehouse.
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button 
            type="button" 
            onClick={onClose} 
            disabled={loading}
            style={{ padding: '8px 16px', background: '#e2e8f0', color: '#334155', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 500 }}
          >
            Cancel
          </button>
          <button 
            type="submit" 
            disabled={loading}
            style={{ padding: '8px 16px', background: '#16a34a', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
          >
            {loading ? 'Receiving...' : 'Confirm Stock In'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { PurchaseService } from '../../services/purchaseService';
import { productService } from '../../services/products';



// Using inline styles for simplicity since this is an MVP
export default function CreatePurchase() {
  const { user } = useAuthStore();
  const [vendorName, setVendorName] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [items, setItems] = useState([{ product_sku: '', description: '', qty: 1, unit_cost: 0, gst_pct: 0, hsn: '' }]);
  const [warehouseId, setWarehouseId] = useState('');
  const [loading, setLoading] = useState(false);
  const [draftId, setDraftId] = useState(null);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  
  // Use a stable idempotency key for this session
  const [draftIdempotency] = useState(crypto.randomUUID());
  const [allProducts, setAllProducts] = useState([]);
  
  
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const prods = await productService.getProducts();
        setAllProducts(prods);
      } catch (e) {
        console.error("Failed to load products", e);
      }
    };
    fetchProducts();

    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const handleAddItem = () => {
    setItems([...items, { product_sku: '', description: '', qty: 1, unit_cost: 0, gst_pct: 0, hsn: '' }]);
  };

  const updateItem = (index, field, value) => {
    const newItems = [...items];
    newItems[index][field] = value;
    
    // Auto-fill if SKU is entered
    if (field === 'product_sku') {
      const match = allProducts.find(p => p.sku.toLowerCase() === value.toLowerCase());
      if (match) {
        newItems[index].description = match.name || '';
        newItems[index].hsn = match.hsn || '';
        newItems[index].unit_cost = match.item_rate || 0;
      }
    }
    
    setItems(newItems);
  };

  const handleSaveDraft = async () => {
    try {
      setLoading(true);
      const payload = {
        idempotency_key: draftIdempotency,
        company_id: user?.company_id || 1, // fallback
        vendor_name: vendorName,
        invoice_number: invoiceNumber,
        items: items.map(i => ({
          ...i,
          qty: parseFloat(i.qty),
          unit_cost: parseFloat(i.unit_cost),
          gst_pct: parseFloat(i.gst_pct)
        })),
        warehouse_id: warehouseId ? parseInt(warehouseId) : null
      };

      const res = await PurchaseService.createDraft(payload);
      if (res.status === 'PENDING') {
        alert('Saved to offline queue!');
      } else {
        setDraftId(res.id);
        alert(`Draft created successfully! ID: ${res.id}`);
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReceive = async () => {
    if (!draftId) {
      alert("Please save draft first.");
      return;
    }
    if (user?.role !== 'ADMIN' && user?.role !== 'MANAGER') {
      alert("You do not have permission to receive stock.");
      return;
    }
    try {
      setLoading(true);
      const res = await PurchaseService.receivePurchase(draftId, {
        idempotency_key: `recv-${draftIdempotency}`,
        warehouse_id: warehouseId ? parseInt(warehouseId) : null
      });
      alert(`Received successfully! Added ${res.movements} inventory records.`);
      // Reset form
      setDraftId(null);
      setVendorName('');
      setInvoiceNumber('');
      setItems([{ product_sku: '', description: '', qty: 1, unit_cost: 0, gst_pct: 0, hsn: '' }]);
    } catch (e) {
      alert(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncOffline = async () => {
    if (isOffline) return alert("You are offline!");
    setLoading(true);
    try {
      const res = await PurchaseService.syncOffline(user?.company_id || 1);
      alert(`Synced ${res.synced} offline records!`);
    } catch (e) {
      alert("Sync failed: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Create Micro-Shipment (Purchase)</h2>
        {isOffline && <span style={{ background: 'red', color: 'white', padding: '4px 8px', borderRadius: '4px' }}>OFFLINE MODE</span>}
      </div>
      
      {PurchaseService.getOfflineQueue().length > 0 && !isOffline && (
        <div style={{ background: '#fff3cd', padding: '10px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between' }}>
          <span>You have pending offline purchases.</span>
          <button onClick={handleSyncOffline} disabled={loading}>Sync Now</button>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div>
          <label>Vendor Name: </label>
          <input value={vendorName} onChange={e => setVendorName(e.target.value)} required style={{ width: '100%', padding: '8px' }} />
        </div>
        
        <div>
          <label>Invoice Number (Optional): </label>
          <input value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} style={{ width: '100%', padding: '8px' }} />
        </div>
        
        <div>
          <label>Target Warehouse ID (Optional, defaults to Central): </label>
          <input type="number" value={warehouseId} onChange={e => setWarehouseId(e.target.value)} style={{ width: '100%', padding: '8px' }} />
        </div>

        <h4>Items</h4>
        
        <datalist id="sku-list">
          {allProducts.map(p => (
            <option key={p.sku} value={p.sku}>{p.name}</option>
          ))}
        </datalist>
        
        {items.map((item, index) => (

          <div key={index} style={{ display: 'flex', gap: '10px', background: '#f9f9f9', padding: '10px', borderRadius: '4px' }}>
            <input placeholder="SKU" list="sku-list" value={item.product_sku} onChange={e => updateItem(index, 'product_sku', e.target.value)} style={{ flex: 1 }} />
            <input placeholder="Description (Auto-creates product if new)" value={item.description} onChange={e => updateItem(index, 'description', e.target.value)} style={{ flex: 2 }} />
            <input placeholder="Qty" type="number" value={item.qty} onChange={e => updateItem(index, 'qty', e.target.value)} style={{ width: '60px' }} />
            <input placeholder="Cost" type="number" value={item.unit_cost} onChange={e => updateItem(index, 'unit_cost', e.target.value)} style={{ width: '80px' }} />
            <input placeholder="GST%" type="number" value={item.gst_pct} onChange={e => updateItem(index, 'gst_pct', e.target.value)} style={{ width: '60px' }} />
          </div>
        ))}
        
        <button onClick={handleAddItem} type="button" style={{ width: '120px', padding: '8px' }}>+ Add Item</button>

        <hr />
        
        <div style={{ display: 'flex', gap: '15px' }}>
          <button onClick={handleSaveDraft} disabled={loading} style={{ padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {loading ? 'Saving...' : 'Save Draft'}
          </button>
          
          <button onClick={handleReceive} disabled={loading || !draftId || isOffline} style={{ padding: '10px 20px', background: draftId ? '#28a745' : '#ccc', color: 'white', border: 'none', borderRadius: '4px', cursor: draftId ? 'pointer' : 'not-allowed' }}>
            Receive (Stock In)
          </button>
        </div>
      </div>
    </div>
  );
}

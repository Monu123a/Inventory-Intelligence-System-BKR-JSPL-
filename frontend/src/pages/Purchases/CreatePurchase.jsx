import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import useCompanyStore from '../../stores/useCompanyStore';
import { PurchaseService } from '../../services/purchaseService';
import { productService } from '../../services/products';

export default function CreatePurchase() {
  const { user } = useAuthStore();
  const { currentCompany } = useCompanyStore();
  const activeCompanyId = currentCompany?.id || 2;
  
  const [vendorName, setVendorName] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [items, setItems] = useState([{ product_sku: '', description: '', qty: 1, unit_cost: 0, gst_pct: 0, hsn: '' }]);
  const [warehouseId, setWarehouseId] = useState('');
  const [loading, setLoading] = useState(false);
  const [draftId, setDraftId] = useState(null);
  
  // Payment Options
  const [paymentMethod, setPaymentMethod] = useState('Cash');
  const [amountPaid, setAmountPaid] = useState('');
  const [paymentNotes, setPaymentNotes] = useState('');

  const [isOffline, setIsOffline] = useState(!navigator.onLine);
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

  const handleAddItem = () => setItems([...items, { product_sku: '', description: '', qty: 1, unit_cost: 0, gst_pct: 0, hsn: '' }]);

  const updateItem = (index, field, value) => {
    const newItems = [...items];
    newItems[index][field] = value;
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

  const calculateTotal = () => {
    return items.reduce((sum, item) => sum + (parseFloat(item.qty || 0) * parseFloat(item.unit_cost || 0) * (1 + parseFloat(item.gst_pct || 0)/100)), 0);
  };

  const handleSaveDraft = async () => {
    try {
      setLoading(true);
      const payload = {
        idempotency_key: draftIdempotency,
        company_id: activeCompanyId,
        vendor_name: vendorName,
        invoice_number: invoiceNumber || null,
        items: items.map(i => ({
          ...i,
          qty: parseFloat(i.qty || 0),
          unit_cost: parseFloat(i.unit_cost || 0),
          gst_pct: parseFloat(i.gst_pct || 0)
        })),
        warehouse_id: warehouseId ? parseInt(warehouseId) : null
      };

      const res = await PurchaseService.createDraft(payload);
      if (res.status === 'PENDING') {
        alert('Saved to offline queue!');
      } else {
        setDraftId(res.id);
        alert(`Draft created successfully! Bill ID: ${res.id}`);
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handleReceiveAndPay = async () => {
    if (!draftId) {
      alert("Please save the bill as a draft first before receiving/paying.");
      return;
    }
    try {
      setLoading(true);
      
      // Step 1: Receive Stock
      const recvRes = await PurchaseService.receivePurchase(draftId, {
        idempotency_key: `recv-${draftIdempotency}`,
        warehouse_id: warehouseId ? parseInt(warehouseId) : null
      });
      
      let msg = `Stock received! Added ${recvRes.movements} inventory records.`;
      
      // Step 2: Pay if amount entered
      if (parseFloat(amountPaid) > 0) {
         await PurchaseService.recordPayment(draftId, {
             amount: parseFloat(amountPaid),
             method: paymentMethod,
             notes: paymentNotes
         });
         msg += ` Payment of ₹${amountPaid} recorded.`;
      }

      alert(msg);
      window.location.href = '/purchases'; // Redirect to list instead of crashing component state!
    } catch (e) {
      alert(e.response?.data?.detail || e.message || "An error occurred during receive/pay.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Create Purchase Bill (Micro-Shipment)</h2>
        {isOffline && <span style={{ background: 'red', color: 'white', padding: '4px 8px', borderRadius: '4px' }}>OFFLINE MODE</span>}
      </div>

      <div style={{ background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px' }}>Vendor Name</label>
            <input value={vendorName} onChange={e => setVendorName(e.target.value)} required style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} placeholder="Enter Vendor Name..." />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px' }}>Invoice Number (Optional)</label>
            <input value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} placeholder="e.g. INV-1001" />
          </div>
        </div>

        <h4 style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '15px' }}>Line Items</h4>
        <datalist id="sku-list">
          {allProducts.map(p => <option key={p.sku} value={p.sku}>{p.name}</option>)}
        </datalist>
        
        {items.map((item, index) => (
          <div key={index} style={{ display: 'flex', gap: '10px', marginBottom: '10px', background: '#f9f9f9', padding: '10px', borderRadius: '4px', alignItems: 'center' }}>
            <input placeholder="SKU" list="sku-list" value={item.product_sku} onChange={e => updateItem(index, 'product_sku', e.target.value)} style={{ flex: 1, padding: '8px' }} />
            <input placeholder="Product Name" value={item.description} onChange={e => updateItem(index, 'description', e.target.value)} style={{ flex: 2, padding: '8px' }} />
            <input placeholder="Qty" type="number" value={item.qty} onChange={e => updateItem(index, 'qty', e.target.value)} style={{ width: '70px', padding: '8px' }} />
            <input placeholder="Unit Cost" type="number" value={item.unit_cost} onChange={e => updateItem(index, 'unit_cost', e.target.value)} style={{ width: '90px', padding: '8px' }} />
            <input placeholder="GST %" type="number" value={item.gst_pct} onChange={e => updateItem(index, 'gst_pct', e.target.value)} style={{ width: '70px', padding: '8px' }} />
          </div>
        ))}
        <button onClick={handleAddItem} style={{ padding: '8px 16px', background: '#f0f0f0', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}>+ Add Item</button>

        <div style={{ marginTop: '30px', borderTop: '2px solid #eee', paddingTop: '20px' }}>
          <h3 style={{ textAlign: 'right', marginBottom: '20px' }}>Total Amount: ₹ {calculateTotal().toFixed(2)}</h3>
          
          <div style={{ background: '#f0f8ff', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
            <h4 style={{ marginTop: 0 }}>Payment Details (Optional)</h4>
            <div style={{ display: 'flex', gap: '15px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '12px' }}>Amount to Pay Now</label>
                <input type="number" value={amountPaid} onChange={e => setAmountPaid(e.target.value)} placeholder={`e.g. ${calculateTotal().toFixed(2)}`} style={{ width: '100%', padding: '8px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '12px' }}>Payment Method</label>
                <select value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)} style={{ width: '100%', padding: '8px' }}>
                  <option value="Cash">Cash</option>
                  <option value="Credit">Credit</option>
                  <option value="Bank Transfer">Bank Transfer</option>
                  <option value="UPI">UPI</option>
                  <option value="Check">Check</option>
                </select>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end' }}>
            <button onClick={handleSaveDraft} disabled={loading} style={{ padding: '12px 24px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              {loading ? 'Processing...' : (draftId ? 'Draft Saved ✓' : '1. Save Bill')}
            </button>
            <button onClick={handleReceiveAndPay} disabled={loading || !draftId || isOffline} style={{ padding: '12px 24px', background: draftId ? '#28a745' : '#ccc', color: 'white', border: 'none', borderRadius: '4px', cursor: draftId ? 'pointer' : 'not-allowed', fontWeight: 'bold' }}>
              2. Complete Purchase (Receive & Pay)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

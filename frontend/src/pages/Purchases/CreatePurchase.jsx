import { useQuery } from '@tanstack/react-query';
import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import useCompanyStore from '../../stores/useCompanyStore';
import api from '../../services/api';
import { PurchaseService } from '../../services/purchaseService';
import { productService } from '../../services/products';

export default function CreatePurchase() {
  const { user } = useAuthStore();
  const { currentCompany } = useCompanyStore();
  const activeCompanyId = currentCompany?.id || 2;
  
  const [vendorName, setVendorName] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [billDate, setBillDate] = useState(new Date().toISOString().split('T')[0]);
  const [paymentTerms, setPaymentTerms] = useState('');
  const [ewayBill, setEwayBill] = useState('');
  const [vehicleNo, setVehicleNo] = useState('');
  const [items, setItems] = useState([{ product_sku: '', description: '', qty: 1, unit_cost: 0, gst_pct: 0, hsn: '' }]);
  const [warehouseId, setWarehouseId] = useState('');
  const [loading, setLoading] = useState(false);
  const [draftId, setDraftId] = useState(null);
  
  // Payment Options
  const [paymentMethod, setPaymentMethod] = useState('Cash');
  const [amountPaid, setAmountPaid] = useState('');
  const [warehouses, setWarehouses] = useState([]);
  const [paymentNotes, setPaymentNotes] = useState('');
  const [txnRef, setTxnRef] = useState('');

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

  
  const { data: vendors = [] } = useQuery({
    queryKey: ['vendors'],
    queryFn: async () => {
      const res = await api.get('/api/vendors/');
      return res.data;
    }
  });

  const { data: warehousesQuery = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const res = await api.get('/api/warehouses/');
      return res.data;
    }
  });

  useEffect(() => {
    if (warehousesQuery.length > 0 && warehouses.length === 0) {
      setWarehouses(warehousesQuery);
      if (!warehouseId) {
        setWarehouseId(warehousesQuery[0].id);
      }
    }
  }, [warehousesQuery, warehouses, warehouseId]);

  const handleVendorSelect = (value) => {
    setVendorName(value);
  };

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
        newItems[index].gst_pct = match.default_gst_rate || 0;
      }
    }
    if (field === 'description') {
      const match = allProducts.find(p => p.name.toLowerCase() === value.toLowerCase());
      if (match) {
        newItems[index].product_sku = match.sku || '';
        newItems[index].hsn = match.hsn || '';
        newItems[index].unit_cost = match.item_rate || 0;
        newItems[index].gst_pct = match.default_gst_rate || 0;
      }
    }
    setItems(newItems);
  };

  const calculateTotal = () => {
    return items.reduce((sum, item) => sum + (parseFloat(item.qty || 0) * parseFloat(item.unit_cost || 0) * (1 + parseFloat(item.gst_pct || 0)/100)), 0);
  };

  const handleError = (e) => {
    const detail = e.response?.data?.detail;
    if (Array.isArray(detail)) {
      alert(detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n'));
    } else {
      alert(detail || e.message || "An error occurred");
    }
  };

  const handleSaveDraft = async () => {
    try {
      setLoading(true);
      const payload = {
        idempotency_key: draftIdempotency,
        company_id: activeCompanyId,
        vendor_name: vendorName,
        invoice_number: invoiceNumber || null,
        bill_date: billDate,
        payment_terms: paymentTerms || null,
        eway_bill: ewayBill || null,
        vehicle_number: vehicleNo || null,
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
      handleError(e);
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
      const payAmount = parseFloat(amountPaid);
      if (!isNaN(payAmount) && payAmount > 0) {
         await PurchaseService.recordPayment(draftId, {
             amount: payAmount,
             method: paymentMethod,
             txn_ref: txnRef,
             notes: paymentNotes
         });
         msg += ` Payment of ₹${payAmount} recorded.`;
      }

      alert(msg);
      window.location.href = '/purchases'; // Redirect to list safely
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  const getRefLabel = () => {
    if (paymentMethod === 'UPI') return "UTR Number";
    if (paymentMethod === 'Check') return "Check Number";
    if (paymentMethod === 'Bank Transfer') return "Transaction ID";
    if (paymentMethod === 'Credit') return "Credit Agreement Ref";
    if (paymentMethod === 'EMI') return "EMI Loan ID";
    return "Reference Note";
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1300px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Create Purchase Bill (Micro-Shipment)</h2>
        {isOffline && <span style={{ background: 'red', color: 'white', padding: '4px 8px', borderRadius: '4px' }}>OFFLINE MODE</span>}
      </div>

      <div style={{ background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        
        <div style={{ marginBottom: '20px', background: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#475569', marginBottom: '8px' }}>Receiving Warehouse (Destination for Stock) *</label>
            <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none' }}>
              <option value="">-- Select Warehouse --</option>
              {warehouses.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
          {/* Vendor & General Details */}
          <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#334155', fontSize: '14px', textTransform: 'uppercase' }}>Vendor Details</h4>
            
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#475569' }}>Vendor Name *</label>
              <input list="vendor-names" value={vendorName} onChange={e => handleVendorSelect(e.target.value)} required style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box', outline: 'none' }} placeholder="Select or type Vendor Name..." />
              <datalist id="vendor-names">
                {vendors.map(v => <option key={v.id} value={v.name}>{v.name}</option>)}
              </datalist>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#475569' }}>Payment Terms</label>
                <input value={paymentTerms} onChange={e => setPaymentTerms(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box', outline: 'none' }} placeholder="e.g. Net 30" />
              </div>
            </div>
          </div>

          {/* Invoice Details */}
          <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#334155', fontSize: '14px', textTransform: 'uppercase' }}>Invoice Details</h4>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#475569' }}>Invoice Number</label>
                <input value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box', outline: 'none' }} placeholder="e.g. INV-1001" />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#475569' }}>Bill Date</label>
                <input type="date" value={billDate} onChange={e => setBillDate(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box', outline: 'none' }} />
              </div>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#475569' }}>E-Way Bill No.</label>
                <input value={ewayBill} onChange={e => setEwayBill(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box', outline: 'none' }} placeholder="Optional" />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#475569' }}>Vehicle No.</label>
                <input value={vehicleNo} onChange={e => setVehicleNo(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box', outline: 'none' }} placeholder="Optional" />
              </div>
            </div>
          </div>
        </div>

        {/* LINE ITEMS HEADER */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, color: '#0f172a' }}>Item Details</h3>
        </div>

        <datalist id="sku-list">
          {allProducts.map(p => <option key={p.sku} value={p.sku}>{p.name}</option>)}
        </datalist>
        <datalist id="name-list">
          {allProducts.map(p => <option key={p.sku} value={p.name}>{p.sku}</option>)}
        </datalist>
        
        
        
        <div style={{ overflowX: 'auto', background: 'white', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '1px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '120px' }}>SKU</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase' }}>Product Name</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '140px' }}>HSN</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '80px' }}>Qty</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '140px' }}>Unit Cost</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '80px' }}>GST %</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '100px', textAlign: 'right' }}>Tax Amt</th>
                <th style={{ padding: '12px', fontSize: '13px', color: '#475569', fontWeight: '600', textTransform: 'uppercase', width: '120px', textAlign: 'right' }}>Total</th>
                <th style={{ padding: '12px', width: '40px' }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={index} style={{ borderBottom: index === items.length - 1 ? 'none' : '1px solid #e2e8f0', transition: 'background-color 0.2s' }}>
                  <td style={{ padding: '8px 12px' }}>
                    <input placeholder="SKU" list="sku-list" value={item.product_sku} onChange={e => updateItem(index, 'product_sku', e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', outline: 'none', fontSize: '14px' }} />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <input placeholder="Product Name" list="name-list" value={item.description} onChange={e => updateItem(index, 'description', e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', outline: 'none', fontSize: '14px' }} />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <input placeholder="HSN" value={item.hsn || ''} onChange={e => updateItem(index, 'hsn', e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', outline: 'none', fontSize: '14px' }} />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <input placeholder="Qty" type="number" value={item.qty} onChange={e => updateItem(index, 'qty', e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', outline: 'none', fontSize: '14px' }} />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <input placeholder="Cost" type="number" value={item.unit_cost} onChange={e => updateItem(index, 'unit_cost', e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', outline: 'none', fontSize: '14px' }} />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <input placeholder="GST%" type="number" value={item.gst_pct} onChange={e => updateItem(index, 'gst_pct', e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', outline: 'none', fontSize: '14px' }} />
                  </td>
                  <td style={{ padding: '8px 12px', fontSize: '14px', textAlign: 'right', color: '#64748b' }}>
                    ₹{Math.round(((item.qty || 0) * (item.unit_cost || 0) * (item.gst_pct || 0)) / 100)}
                  </td>
                  <td style={{ padding: '8px 12px', fontSize: '14px', textAlign: 'right', fontWeight: '600', color: '#0f172a' }}>
                    ₹{Math.round((item.qty || 0) * (item.unit_cost || 0) * (1 + (item.gst_pct || 0) / 100))}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                    <button onClick={() => { const newItems = [...items]; newItems.splice(index, 1); setItems(newItems); }} style={{ background: '#fee2e2', color: '#ef4444', border: 'none', borderRadius: '4px', cursor: 'pointer', width: '28px', height: '28px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', fontWeight: 'bold' }} title="Remove Item">&times;</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ padding: '12px', background: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
            <button onClick={handleAddItem} style={{ padding: '8px 16px', background: 'white', color: '#3b82f6', border: '1px solid #bfdbfe', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '14px', transition: 'all 0.2s', width: '100%' }}>+ Add New Line Item</button>
          </div>
        </div>

        <div style={{ marginTop: '30px', borderTop: '2px solid #eee', paddingTop: '20px' }}>
          <h3 style={{ textAlign: 'right', marginBottom: '20px' }}>Total Amount: ₹ {Math.round(calculateTotal())}</h3>
          
          <div style={{ background: '#f0f8ff', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
            <h4 style={{ marginTop: 0 }}>Payment Details (Optional)</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px' }}>Amount to Pay Now</label>
                <input type="number" value={amountPaid} onChange={e => setAmountPaid(e.target.value)} placeholder={`e.g. ${calculateTotal().toFixed(2)}`} style={{ width: '100%', padding: '8px' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px' }}>Payment Method</label>
                <select value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)} style={{ width: '100%', padding: '8px' }}>
                  <option value="Cash">Cash</option>
                  <option value="Credit">Credit</option>
                  <option value="EMI">EMI</option>
                  <option value="Bank Transfer">Bank Transfer</option>
                  <option value="UPI">UPI</option>
                  <option value="Check">Check</option>
                </select>
              </div>
              {paymentMethod !== 'Cash' && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#0056b3' }}>{getRefLabel()}</label>
                  <input type="text" value={txnRef} onChange={e => setTxnRef(e.target.value)} placeholder={getRefLabel()} style={{ width: '100%', padding: '8px', border: '1px solid #0056b3' }} />
                </div>
              )}
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

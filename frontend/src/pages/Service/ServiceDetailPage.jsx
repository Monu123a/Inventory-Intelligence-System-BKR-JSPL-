import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';
import ServiceBillRenderer from './ServiceBillRenderer';

export default function ServiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const currentCompany = useCompanyStore(state => state.currentCompany);
  
  const [service, setService] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [replacementData, setReplacementData] = useState({ itemId: '', replacementItemId: '', quantity: 1 });
  const [billData, setBillData] = useState({ labour_charges: 0, spare_charges: 0, tax_amount: 0 });
  const [newStatus, setNewStatus] = useState('');
  
  const [showBill, setShowBill] = useState(false);

  const fetchService = () => {
    setLoading(true);
    api.get(`/api/services/${id}`)
      .then(res => {
        setService(res.data);
        setNewStatus(res.data.status);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (currentCompany?.id && id) {
      fetchService();
    }
  }, [currentCompany, id]);

  const handleUpdateStatus = async () => {
    if (newStatus === service.status) return;
    try {
      await api.post(`/api/services/${id}/status`, { status: newStatus });
      fetchService();
    } catch (err) {
      console.error(err);
      alert('Failed to update status');
    }
  };

  const handleAddReplacement = async () => {
    if (!replacementData.itemId || !replacementData.replacementItemId) return;
    try {
      await api.post(`/api/services/items/${replacementData.itemId}/replacement?replacement_product_id=${replacementData.replacementItemId}&quantity=${replacementData.quantity}`);
      fetchService();
      setReplacementData({ itemId: '', replacementItemId: '', quantity: 1 });
    } catch (err) {
      console.error(err);
      alert('Failed to add replacement');
    }
  };

  const handleSetBill = async () => {
    try {
      await api.post(`/api/services/${id}/bill?labour_charges=${billData.labour_charges || 0}&spare_charges=${billData.spare_charges || 0}&tax_amount=${billData.tax_amount || 0}`);
      fetchService();
    } catch (err) {
      console.error(err);
      alert('Failed to set bill');
    }
  };

  if (loading) return <div style={{ padding: '24px', textAlign: 'center' }}>Loading...</div>;
  if (!service) return <div style={{ padding: '24px', textAlign: 'center' }}>Service record not found</div>;

  if (showBill) {
    return (
      <div style={{ padding: '24px' }}>
        <button onClick={() => setShowBill(false)} style={{ marginBottom: '16px', padding: '8px 16px', backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer' }}>Back</button>
        <button onClick={() => window.print()} style={{ marginBottom: '16px', marginLeft: '12px', padding: '8px 16px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Print</button>
        <ServiceBillRenderer service={service} company={currentCompany} />
      </div>
    );
  }

  const sectionStyle = { backgroundColor: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Service Record #{service.id}</h2>
        <button onClick={() => navigate('/service/records')} style={{ padding: '8px 16px', backgroundColor: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer' }}>Back to Records</button>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ marginTop: 0 }}>Details</h3>
        <p><strong>Customer:</strong> {service.customer_name || 'N/A'}</p>
        <p><strong>Type:</strong> {service.service_type}</p>
        <p><strong>Complaint:</strong> {service.complaint}</p>
        <p><strong>Date:</strong> {new Date(service.created_at || service.date).toLocaleString()}</p>
        <p><strong>Status:</strong> <span style={{ padding: '4px 8px', backgroundColor: service.status === 'Completed' ? '#dcfce7' : '#dbeafe', color: service.status === 'Completed' ? '#166534' : '#1e40af', borderRadius: '9999px', fontSize: '12px', fontWeight: '500' }}>{service.status}</span></p>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ marginTop: 0 }}>Update Status</h3>
        <div style={{ display: 'flex', gap: '12px' }}>
          <select 
            value={newStatus} 
            onChange={(e) => setNewStatus(e.target.value)}
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          <button onClick={handleUpdateStatus} style={{ padding: '8px 16px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Update</button>
        </div>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ marginTop: 0 }}>Items & Replacements</h3>
        {service.items && service.items.length > 0 ? (
          <ul style={{ paddingLeft: '20px' }}>
            {service.items.map(item => (
              <li key={item.id} style={{ marginBottom: '8px' }}>
                Item ID: {item.id} - Sale Item: {item.sku_snapshot || 'N/A'} (Qty: {item.quantity})
                {item.replacement_product_id ? (
                  <span style={{ marginLeft: '12px', color: '#166534', fontWeight: '500' }}>(Replaced with Product ID: {item.replacement_product_id}, Qty: {item.replacement_quantity})</span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p>No items associated.</p>
        )}
        
        <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f9fafb', borderRadius: '4px', border: '1px solid #e5e7eb' }}>
          <h4 style={{ marginTop: 0 }}>Add Replacement</h4>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <input 
              placeholder="Service Item ID" 
              value={replacementData.itemId} 
              onChange={e => setReplacementData({...replacementData, itemId: e.target.value})} 
              style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
            />
            <input 
              placeholder="Replacement Product ID" 
              value={replacementData.replacementItemId} 
              onChange={e => setReplacementData({...replacementData, replacementItemId: e.target.value})} 
              style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
            />
            <input 
              type="number"
              placeholder="Quantity" 
              value={replacementData.quantity} 
              onChange={e => setReplacementData({...replacementData, quantity: e.target.value})} 
              style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '80px' }}
            />
            <button onClick={handleAddReplacement} style={{ padding: '8px 16px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Add</button>
          </div>
        </div>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ marginTop: 0 }}>Billing</h3>
        <p>Current Total: <strong style={{ fontSize: '18px' }}>₹{service.grand_total || 0}</strong> (Labour: ₹{service.labour_charges || 0}, Spares: ₹{service.spare_charges || 0}, Tax: ₹{service.tax_amount || 0})</p>
        <div style={{ display: 'flex', gap: '12px', marginTop: '12px', flexWrap: 'wrap' }}>
          <input 
            type="number" 
            placeholder="Labour Charges" 
            value={billData.labour_charges} 
            onChange={e => setBillData({ ...billData, labour_charges: e.target.value })} 
            style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '140px' }}
          />
          <input 
            type="number" 
            placeholder="Spare Charges" 
            value={billData.spare_charges} 
            onChange={e => setBillData({ ...billData, spare_charges: e.target.value })} 
            style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '140px' }}
          />
          <input 
            type="number" 
            placeholder="Tax Amount" 
            value={billData.tax_amount} 
            onChange={e => setBillData({ ...billData, tax_amount: e.target.value })} 
            style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '140px' }}
          />
          <button onClick={handleSetBill} style={{ padding: '8px 16px', backgroundColor: '#f59e0b', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Update Bill</button>
        </div>
        
        <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
          <button onClick={() => setShowBill(true)} style={{ padding: '10px 20px', backgroundColor: '#4b5563', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500' }}>
            View / Print Bill
          </button>
        </div>
      </div>

    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';

export default function CreateServicePage() {
  const navigate = useNavigate();
  const currentCompany = useCompanyStore(state => state.currentCompany);
  
  const [sales, setSales] = useState([]);
  const [selectedSaleId, setSelectedSaleId] = useState('');
  const [saleItems, setSaleItems] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState('');
  
  const [serviceData, setServiceData] = useState({
    service_type: 'Repair',
    complaint: ''
  });
  
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (currentCompany?.id) {
      api.get('/api/pos/history?limit=50')
        .then(res => setSales(res.data?.items || res.data || []))
        .catch(err => console.error(err));
    }
  }, [currentCompany]);

  useEffect(() => {
    if (selectedSaleId) {
      api.get(`/api/pos/sales/${selectedSaleId}`)
        .then(res => {
          const invoice = res.data?.receipt;
          if (invoice && invoice.items) {
            setSaleItems(invoice.items);
            setSelectedItemId('');
          }
        })
        .catch(err => {
          console.error(err);
          setSaleItems([]);
          setSelectedItemId('');
        });
    } else {
      setSaleItems([]);
      setSelectedItemId('');
    }
  }, [selectedSaleId]);

  const handleCreate = async () => {
    if (!selectedSaleId) {
      setError('Please select an invoice.');
      return;
    }
    if (!selectedItemId) {
      setError('Please select a product from the invoice.');
      return;
    }
    if (!serviceData.complaint) {
      setError('Please enter a complaint description.');
      return;
    }
    
    setCreating(true);
    setError('');
    
    try {
      const selectedSale = sales.find(s => s.id === parseInt(selectedSaleId));
      const selectedItem = saleItems.find(i => i.id === parseInt(selectedItemId));

      const payload = {
        customer_id: selectedSale?.customer_id || null,
        customer_name_snapshot: selectedSale?.customer_name || 'Unknown',
        customer_mobile_snapshot: selectedSale?.customer_mobile || null,
        customer_email_snapshot: selectedSale?.customer_email || null,
        invoice_number: selectedSale?.bill_number || null,
        sale_type: selectedSale?.sale_type || null,
        marketplace: selectedSale?.marketplace || null,
        service_type: serviceData.service_type,
        complaint: serviceData.complaint,
        items: [
          {
            product_id: selectedItem?.product_id || null,
            sku_snapshot: selectedItem?.sku || null,
            quantity: 1
          }
        ]
      };
      const response = await api.post('/api/services/', payload);
      navigate(`/service/${response.data.id}`);
    } catch (err) {
      console.error(err);
      let errorMessage = 'Failed to create Service Record';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map(e => `${e.loc?.slice(-1)?.[0] || 'Field'}: ${e.msg}`).join(', ');
        }
      }
      setError(errorMessage);
    } finally {
      setCreating(false);
    }
  };

  const inputStyle = { width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' };
  const labelStyle = { display: 'block', marginBottom: '8px', fontWeight: '500' };

  return (
    <div style={{ padding: '24px', maxWidth: '600px', margin: '0 auto', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
      <h2 style={{ marginTop: 0, marginBottom: '24px' }}>Create Service Record</h2>
      
      {error && <div style={{ color: 'red', marginBottom: '16px', padding: '12px', backgroundColor: '#fee2e2', borderRadius: '4px' }}>{error}</div>}
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label style={labelStyle}>Select Invoice (Sale)</label>
          <select 
            value={selectedSaleId}
            onChange={(e) => setSelectedSaleId(e.target.value)}
            style={inputStyle}
          >
            <option value="">-- Select an Invoice --</option>
            {sales.map(sale => (
              <option key={sale.id} value={sale.id}>
                {sale.bill_number} - {sale.customer_name} ({new Date(sale.sale_date).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>

        {saleItems.length > 0 && (
          <div>
            <label style={labelStyle}>Select Product</label>
            <select 
              value={selectedItemId}
              onChange={(e) => setSelectedItemId(e.target.value)}
              style={inputStyle}
            >
              <option value="">-- Select a Product --</option>
              {saleItems.map(item => (
                <option key={item.id} value={item.id}>
                  {item.product_name || item.name} (Qty: {item.quantity})
                </option>
              ))}
            </select>
          </div>
        )}
        
        <div>
          <label style={labelStyle}>Service Type</label>
          <select
            value={serviceData.service_type}
            onChange={(e) => setServiceData({...serviceData, service_type: e.target.value})}
            style={inputStyle}
          >
            <option value="Repair">Repair</option>
            <option value="Replacement">Replacement</option>
            <option value="Installation">Installation</option>
            <option value="General Service">General Service</option>
          </select>
        </div>

        <div>
          <label style={labelStyle}>Complaint / Reason</label>
          <textarea 
            value={serviceData.complaint}
            onChange={(e) => setServiceData({...serviceData, complaint: e.target.value})}
            placeholder="Describe the issue..."
            style={{ ...inputStyle, minHeight: '80px' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
          <button 
            onClick={() => navigate('/service/records')}
            style={{ padding: '10px 20px', background: '#f3f4f6', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}
          >
            Cancel
          </button>
          <button 
            onClick={handleCreate}
            disabled={creating}
            style={{ flex: 1, padding: '10px 20px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500', opacity: creating ? 0.7 : 1 }}
          >
            {creating ? 'Creating...' : 'Create Service Record'}
          </button>
        </div>
      </div>
    </div>
  );
}

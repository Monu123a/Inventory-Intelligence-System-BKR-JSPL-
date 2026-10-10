import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';

export default function VendorsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [activeVendorId, setActiveVendorId] = useState(null);
  
  const [formData, setFormData] = useState({ name: '', contact: '', phone: '', gst_number: '', address: '', bank_details: '', payable_balance: 0 });

  const { data: vendors = [], isLoading } = useQuery({
    queryKey: ['vendors', search],
    queryFn: async () => {
      const res = await api.get(`/api/vendors/?search=${search}`);
      return res.data;
    }
  });

  const { data: vendorHistory, isLoading: loadingHistory } = useQuery({
    queryKey: ['vendorHistory', activeVendorId],
    queryFn: async () => {
      const res = await api.get(`/api/vendors/${activeVendorId}/history`);
      return res.data;
    },
    enabled: !!activeVendorId && isHistoryModalOpen
  });

  const saveMutation = useMutation({
    mutationFn: async (data) => {
      if (editingVendor) {
        return await api.put(`/api/vendors/${editingVendor.id}`, data);
      }
      return await api.post('/api/vendors/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['vendors']);
      setIsModalOpen(false);
      setEditingVendor(null);
      setFormData({ name: '', contact: '', phone: '', gst_number: '', address: '', bank_details: '', payable_balance: 0 });
    }
  });

  const handleOpenModal = (vendor = null) => {
    if (vendor) {
      setEditingVendor(vendor);
      setFormData({ name: vendor.name, contact: vendor.contact || '', phone: vendor.phone || '', gst_number: vendor.gst_number || '', address: vendor.address || '', bank_details: vendor.bank_details || '', payable_balance: vendor.payable_balance || 0 });
    } else {
      setEditingVendor(null);
      setFormData({ name: '', contact: '', phone: '', gst_number: '', address: '', bank_details: '', payable_balance: 0 });
    }
    setIsModalOpen(true);
  };

  const handleViewHistory = (id) => {
    setActiveVendorId(id);
    setIsHistoryModalOpen(true);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: '#111827' }}>Vendor CRM & Ledger</h1>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: '14px' }}>Manage vendors, view history, and track outstanding balances.</p>
        </div>
        <button 
          onClick={() => handleOpenModal()} 
          style={{ background: '#2563eb', color: 'white', border: 'none', padding: '10px 16px', borderRadius: '6px', fontWeight: '500', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          + Add New Vendor
        </button>
      </div>

      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <input 
          type="text" 
          placeholder="Search vendors by name..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px', boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
        {vendors.map(vendor => (
          <div key={vendor.id} style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#111827' }}>{vendor.name}</h3>
                <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '4px' }}>{vendor.contact || 'No contact info'}</div>
              </div>
              <span style={{ background: '#f3f4f6', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '600', color: '#374151' }}>ID: {vendor.id}</span>
            </div>
            
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px', marginBottom: '16px', marginTop: 'auto' }}>
              <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase', fontWeight: '600', letterSpacing: '0.5px' }}>Ledger Balance</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: vendor.payable_balance > 0 ? '#dc2626' : '#16a34a', marginTop: '4px' }}>
                ₹ {parseFloat(vendor.payable_balance).toFixed(2)} {vendor.payable_balance > 0 ? '(Dr)' : '(Cr)'}
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                onClick={() => handleViewHistory(vendor.id)}
                style={{ flex: 1, padding: '8px', background: 'white', border: '1px solid #d1d5db', borderRadius: '6px', color: '#374151', fontSize: '13px', fontWeight: '500', cursor: 'pointer', transition: 'all 0.2s' }}
              >
                View History
              </button>
              <button 
                onClick={() => handleOpenModal(vendor)}
                style={{ flex: 1, padding: '8px', background: 'white', border: '1px solid #d1d5db', borderRadius: '6px', color: '#374151', fontSize: '13px', fontWeight: '500', cursor: 'pointer', transition: 'all 0.2s' }}
              >
                Edit Card
              </button>
            </div>
          </div>
        ))}
        {vendors.length === 0 && !isLoading && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#6b7280' }}>
            No vendors found. Click "Add New Vendor" to create one.
          </div>
        )}
      </div>

      {/* CREATE / EDIT MODAL */}
      {isModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: 'white', width: '100%', maxWidth: '400px', borderRadius: '8px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f9fafb' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>{editingVendor ? 'Edit Vendor Card' : 'Create New Vendor'}</h3>
              <button onClick={() => setIsModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#6b7280' }}>&times;</button>
            </div>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>Vendor Name *</label>
                <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box' }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>Phone Number</label>
                  <input type="text" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>Email</label>
                  <input type="text" value={formData.contact} onChange={e => setFormData({...formData, contact: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box' }} />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>GST Number</label>
                <input type="text" value={formData.gst_number} onChange={e => setFormData({...formData, gst_number: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>Address</label>
                <textarea value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box', minHeight: '60px', resize: 'vertical' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>Bank Details (Optional)</label>
                <textarea value={formData.bank_details} onChange={e => setFormData({...formData, bank_details: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box', minHeight: '60px', resize: 'vertical' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '6px' }}>Ledger Balance (₹)</label>
                <input type="number" value={formData.payable_balance} onChange={e => setFormData({...formData, payable_balance: parseFloat(e.target.value) || 0})} disabled={!!editingVendor} style={{ width: '100%', padding: '10px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box', background: editingVendor ? '#f3f4f6' : 'white' }} />
              </div>
            </div>
            <div style={{ padding: '16px 20px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: '10px', background: '#f9fafb' }}>
              <button onClick={() => setIsModalOpen(false)} style={{ padding: '8px 16px', background: 'white', border: '1px solid #d1d5db', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>Cancel</button>
              <button 
                onClick={() => saveMutation.mutate(formData)} 
                disabled={!formData.name || saveMutation.isLoading}
                style={{ padding: '8px 16px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '500', opacity: (!formData.name || saveMutation.isLoading) ? 0.7 : 1 }}
              >
                {saveMutation.isLoading ? 'Saving...' : 'Save Vendor'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HISTORY MODAL */}
      {isHistoryModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: 'white', width: '90%', maxWidth: '800px', maxHeight: '90vh', borderRadius: '8px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f9fafb' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>{vendorHistory?.vendor?.name} - History & Ledger</h3>
                <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '4px' }}>Total Outstanding: ₹{parseFloat(vendorHistory?.vendor?.payable_balance || 0).toFixed(2)}</div>
              </div>
              <button onClick={() => setIsHistoryModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#6b7280' }}>&times;</button>
            </div>
            
            <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
              {loadingHistory ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>Loading history...</div>
              ) : vendorHistory?.purchases?.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f3f4f6', textAlign: 'left', fontSize: '13px', color: '#374151' }}>
                      <th style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb' }}>Date</th>
                      <th style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb' }}>Invoice Number</th>
                      <th style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb' }}>Status</th>
                      <th style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vendorHistory.purchases.map(p => (
                      <tr key={p.id} style={{ borderBottom: '1px solid #e5e7eb', fontSize: '14px' }}>
                        <td style={{ padding: '12px 16px', color: '#6b7280' }}>{new Date(p.date).toLocaleDateString()}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '500' }}>{p.invoice_number || 'Draft'}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '500', background: p.status === 'COMPLETED' ? '#dcfce7' : '#fef9c3', color: p.status === 'COMPLETED' ? '#166534' : '#854d0e' }}>
                            {p.status}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: '600' }}>₹ {parseFloat(p.total_amount).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280', background: '#f9fafb', borderRadius: '8px', border: '1px dashed #d1d5db' }}>
                  No purchases found for this vendor.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

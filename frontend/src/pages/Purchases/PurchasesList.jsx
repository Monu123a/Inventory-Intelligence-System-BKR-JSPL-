import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import useCompanyStore from '../../stores/useCompanyStore';
import { PurchaseService } from '../../services/purchaseService';
import { DataTable } from '../../components/DataTable/DataTable';
import { PurchaseBillModal } from '../../components/Purchases/PurchaseBillModal';
import { RecordPaymentModal } from '../../components/Purchases/RecordPaymentModal';

export default function PurchasesList() {
  const { user } = useAuthStore();
  const { currentCompany } = useCompanyStore();
  const activeCompanyId = currentCompany?.id || 2;
  
  const [activeTab, setActiveTab] = useState('bills');
  const [payables, setPayables] = useState([]);
  const [purchases, setPurchases] = useState([]);
  
  const [selectedBill, setSelectedBill] = useState(null);
  const [billModalOpen, setBillModalOpen] = useState(false);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [selectedPaymentPurchase, setSelectedPaymentPurchase] = useState(null);

  const loadData = () => {
    if (activeCompanyId) {
      PurchaseService.getPayables(activeCompanyId).then(setPayables).catch(console.error);
      PurchaseService.getPurchases().then(setPurchases).catch(console.error);
    }
  };

  useEffect(() => {
    loadData();
  }, [user, activeCompanyId]);

  const viewBill = async (purchase) => {
    try {
      const full = await PurchaseService.getPurchaseById(purchase.id);
      setSelectedBill(full);
      setBillModalOpen(true);
    } catch(e) {
      alert("Failed to load bill details.");
    }
  };

  const openPayment = (purchase) => {
    setSelectedPaymentPurchase(purchase);
    setPaymentModalOpen(true);
  };

  const receiveDraft = async (purchase) => {
    try {
      if (confirm(`Receive stock for draft bill ${purchase.invoice_number || purchase.id}?`)) {
        await PurchaseService.receivePurchase(purchase.id, {
          idempotency_key: `recv-${crypto.randomUUID()}`,
          warehouse_id: null // defaults to central
        });
        alert("Stock received successfully!");
        loadData();
      }
    } catch(e) {
      const detail = e.response?.data?.detail;
      if (Array.isArray(detail)) {
        alert(detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n'));
      } else {
        alert(detail || e.message || "An error occurred");
      }
    }
  };

  const vendorColumns = [
    { name: 'Vendor Name', key: 'name', render: (_, r) => <strong>{r.name}</strong> },
    { name: 'Total Payable Balance', key: 'payable_balance', render: (_, r) => {
        const bal = Number(r.payable_balance || 0);
        return <span style={{ color: bal > 0 ? '#d9534f' : '#5cb85c', fontWeight: 'bold' }}>₹ {bal.toFixed(2)}</span>;
    }}
  ];

  const billColumns = [
    { name: 'Bill ID', key: 'id', render: (_, r) => r.invoice_number || `PUR-${r.id}` },
    { name: 'Vendor', key: 'vendor_name' },
    { name: 'Bill Amount', key: 'total_amount', render: (_, r) => `₹ ${Number(r.total_amount||0).toFixed(2)}` },
    { name: 'Amount Paid', key: 'amount_paid', render: (_, r) => `₹ ${Number(r.amount_paid||0).toFixed(2)}` },
    { name: 'Payment Status', key: 'payment_status', render: (_, r) => (
      <span style={{ padding: '4px 8px', borderRadius: '12px', fontSize: '12px', background: r.payment_status === 'PAID' ? '#d4edda' : (r.payment_status === 'PARTIAL' ? '#fff3cd' : '#f8d7da') }}>
        {r.payment_status}
      </span>
    )},
    { name: 'Method', key: 'payment_method', render: (_, r) => r.payment_method || '-' },
    { name: 'Stock Status', key: 'status', render: (_, r) => (
      <span style={{ fontWeight: 'bold', color: r.status === 'RECEIVED' ? 'green' : 'orange' }}>{r.status}</span>
    )},
    { name: 'Actions', key: 'actions', render: (_, r) => (
      <div style={{ display: 'flex', gap: '8px' }}>
        <button onClick={() => viewBill(r)} style={{ cursor: 'pointer', padding: '4px 8px', background: '#f8f9fa', border: '1px solid #ddd', borderRadius: '4px' }}>View Bill</button>
        {r.status === 'DRAFT' && (
          <button onClick={() => receiveDraft(r)} style={{ cursor: 'pointer', padding: '4px 8px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}>Receive</button>
        )}
        {r.payment_status !== 'PAID' && r.status === 'RECEIVED' && (
          <button onClick={() => openPayment(r)} style={{ cursor: 'pointer', padding: '4px 8px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}>Pay</button>
        )}
      </div>
    ) }
  ];

  return (
    <div style={{ padding: '20px' }}>
      <h2>Purchase Bills & Vendor Ledgers</h2>
      
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', borderBottom: '1px solid #ddd', paddingBottom: '10px' }}>
        <button onClick={() => setActiveTab('bills')} style={{ padding: '10px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', fontWeight: activeTab === 'bills' ? 'bold' : 'normal', color: activeTab === 'bills' ? '#007bff' : '#333', borderBottom: activeTab === 'bills' ? '3px solid #007bff' : 'none' }}>Purchase Bills</button>
        <button onClick={() => setActiveTab('vendors')} style={{ padding: '10px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', fontWeight: activeTab === 'vendors' ? 'bold' : 'normal', color: activeTab === 'vendors' ? '#007bff' : '#333', borderBottom: activeTab === 'vendors' ? '3px solid #007bff' : 'none' }}>Vendor Ledgers</button>
      </div>
      
      {activeTab === 'bills' ? (
        <DataTable title="All Purchase Bills" columns={billColumns} data={purchases} pagination />
      ) : (
        <DataTable title="Outstanding Vendor Balances" columns={vendorColumns} data={payables} pagination />
      )}
      
      <PurchaseBillModal isOpen={billModalOpen} onClose={() => setBillModalOpen(false)} purchase={selectedBill} />
      <RecordPaymentModal isOpen={paymentModalOpen} onClose={() => setPaymentModalOpen(false)} purchase={selectedPaymentPurchase} onSuccess={() => { setPaymentModalOpen(false); loadData(); }} />
    </div>
  );
}

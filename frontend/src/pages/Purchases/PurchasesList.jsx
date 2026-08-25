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
      alert("Failed to load bill");
    }
  };

  const openPayment = (purchase) => {
    setSelectedPaymentPurchase(purchase);
    setPaymentModalOpen(true);
  };

  const vendorColumns = [
    { name: 'ID', key: 'id' },
    { name: 'Vendor Name', key: 'name' },
    { name: 'Total Payable Balance (₹)', key: 'payable_balance', render: (_, row) => Number(row.payable_balance || 0).toFixed(2) },
  ];

  const billColumns = [
    { name: 'Invoice #', key: 'invoice_number' },
    { name: 'Vendor', key: 'vendor_name' },
    { name: 'Total Amount', key: 'total_amount', render: (_, r) => `₹ ${Number(r.total_amount||0).toFixed(2)}` },
    { name: 'Paid', key: 'amount_paid', render: (_, r) => `₹ ${Number(r.amount_paid||0).toFixed(2)}` },
    { name: 'Payment Status', key: 'payment_status' },
    { name: 'Method', key: 'payment_method' },
    { name: 'Actions', key: 'id', render: (_, r) => (
      <div style={{ display: 'flex', gap: '8px' }}>
        <button onClick={() => viewBill(r)} style={{ cursor: 'pointer' }}>View Bill</button>
        {r.payment_status !== 'PAID' && r.status === 'RECEIVED' && (
          <button onClick={() => openPayment(r)} style={{ cursor: 'pointer', background: 'blue', color: 'white' }}>Pay</button>
        )}
      </div>
    ) }
  ];

  return (
    <div style={{ padding: '20px' }}>
      <h2>Vendor Payables & Purchases</h2>
      
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', borderBottom: '1px solid #ccc', paddingBottom: '10px' }}>
        <button onClick={() => setActiveTab('bills')} style={{ fontWeight: activeTab === 'bills' ? 'bold' : 'normal' }}>Purchase Bills</button>
        <button onClick={() => setActiveTab('vendors')} style={{ fontWeight: activeTab === 'vendors' ? 'bold' : 'normal' }}>Vendor Ledgers</button>
      </div>
      
      {activeTab === 'bills' ? (
        <DataTable title="Purchase Bills" columns={billColumns} data={purchases} pagination />
      ) : (
        <DataTable title="Vendor Balances" columns={vendorColumns} data={payables} pagination />
      )}
      
      <PurchaseBillModal isOpen={billModalOpen} onClose={() => setBillModalOpen(false)} purchase={selectedBill} />
      <RecordPaymentModal isOpen={paymentModalOpen} onClose={() => setPaymentModalOpen(false)} purchase={selectedPaymentPurchase} onSuccess={() => { setPaymentModalOpen(false); loadData(); }} />
    </div>
  );
}

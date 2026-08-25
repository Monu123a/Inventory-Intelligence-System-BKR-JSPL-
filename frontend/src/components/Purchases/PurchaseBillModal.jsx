import React from 'react';
import { Modal } from '../Modal/Modal';
import { DataTable } from '../DataTable/DataTable';

export const PurchaseBillModal = ({ isOpen, onClose, purchase }) => {
  if (!purchase) return null;

  const columns = [
    { name: 'SKU', key: 'product_sku' },
    { name: 'Description', key: 'description' },
    { name: 'Qty', key: 'qty' },
    { name: 'Unit Cost', key: 'unit_cost', render: (_, r) => `₹ ${Number(r.unit_cost||0).toFixed(2)}` },
    { name: 'GST %', key: 'gst_pct', render: (_, r) => `${Number(r.gst_pct||0).toFixed(1)}%` },
    { name: 'Line Total', key: 'line_total', render: (_, r) => `₹ ${Number(r.line_total||0).toFixed(2)}` },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Purchase Bill - ${purchase.invoice_number || purchase.id}`}>
      <div style={{ marginBottom: '20px' }}>
        <p><strong>Vendor:</strong> {purchase.vendor_name}</p>
        <p><strong>Date:</strong> {new Date(purchase.created_at).toLocaleDateString()}</p>
        <p><strong>Status:</strong> {purchase.status}</p>
        <p><strong>Payment Status:</strong> <span style={{ color: purchase.payment_status === 'UNPAID' ? 'red' : 'green' }}>{purchase.payment_status}</span></p>
        {purchase.payment_method && <p><strong>Method:</strong> {purchase.payment_method}</p>}
        <p><strong>Total Amount:</strong> ₹ {Number(purchase.total_amount || 0).toFixed(2)}</p>
        <p><strong>Amount Paid:</strong> ₹ {Number(purchase.amount_paid || 0).toFixed(2)}</p>
      </div>
      
      <DataTable
        columns={columns}
        data={purchase.items}
      />
      
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
        <button onClick={onClose} style={{ padding: '8px 16px', background: '#ccc', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Close</button>
      </div>
    </Modal>
  );
};

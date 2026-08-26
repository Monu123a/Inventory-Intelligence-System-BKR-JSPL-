import React from 'react';
import { Modal } from '../../components/Modal/Modal';
import InvoiceRenderer from '../../components/invoice/InvoiceRenderer';
import styles from './POSPage.module.css'; // Just re-using some button styles

export default function InvoicePreviewModal({ invoice, onClose, onComplete, isPending }) {
  if (!invoice) return null;

  return (
    <Modal isOpen={true} onClose={onClose} title="Invoice Preview" maxWidth="900px">
      <div style={{ maxHeight: '70vh', overflowY: 'auto', border: '1px solid #e2e8f0', marginBottom: '16px', padding: '16px', background: '#fff' }}>
        <InvoiceRenderer invoice={invoice} />
      </div>
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
        <button 
          onClick={onClose}
          style={{ padding: '8px 16px', background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer' }}
        >
          Back to Edit
        </button>
        <button
          onClick={onComplete}
          disabled={isPending}
          style={{ padding: '8px 16px', background: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: isPending ? 'not-allowed' : 'pointer' }}
        >
          {isPending ? 'Processing...' : 'Complete Sale'}
        </button>
      </div>
    </Modal>
  );
}

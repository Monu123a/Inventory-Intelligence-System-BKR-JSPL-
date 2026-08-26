import React, { useState } from 'react';
import { Modal } from '../Modal/Modal';
import Input from '../forms/Input';
import { PurchaseService } from '../../services/purchaseService';

export const RecordPaymentModal = ({ isOpen, onClose, purchase, onSuccess }) => {
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('CASH');
  const [txnRef, setTxnRef] = useState('');
  const [loading, setLoading] = useState(false);

  if (!purchase) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await PurchaseService.recordPayment(purchase.id, {
        amount: parseFloat(amount),
        method,
        txn_ref: txnRef
      });
      onSuccess();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        alert(detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n'));
      } else {
        alert(detail || err.message || "Error recording payment");
      }
    } finally {
      setLoading(false);
    }
  };

  const getRefLabel = () => {
    if (method === 'UPI') return "UTR Number";
    if (method === 'CHECK') return "Check Number";
    if (method === 'BANK_TRANSFER') return "Transaction ID";
    if (method === 'CREDIT') return "Credit Agreement Ref";
    if (method === 'EMI') return "EMI Loan ID";
    return "Reference Note";
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Record Payment for ${purchase.invoice_number || purchase.id}`}>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label>Payment Method</label>
          <select value={method} onChange={e => setMethod(e.target.value)} style={{ display: 'block', width: '100%', padding: '8px', marginTop: '5px' }}>
            <option value="CASH">Cash</option>
            <option value="CREDIT">Credit</option>
            <option value="EMI">EMI</option>
            <option value="CHECK">Check</option>
            <option value="BANK_TRANSFER">Bank Transfer</option>
            <option value="UPI">UPI</option>
          </select>
        </div>
        <Input 
          label="Amount (₹)" 
          type="number" 
          step="0.01" 
          value={amount} 
          onChange={e => setAmount(e.target.value)} 
          required
        />
        
        {method !== 'CASH' && (
          <Input 
            label={`${getRefLabel()} (Optional)`} 
            value={txnRef} 
            onChange={e => setTxnRef(e.target.value)} 
          />
        )}
        
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
          <button type="button" onClick={onClose} style={{ padding: '8px 16px', background: '#ccc', border: 'none', borderRadius: '4px' }}>Cancel</button>
          <button type="submit" disabled={loading} style={{ padding: '8px 16px', background: 'blue', color: 'white', border: 'none', borderRadius: '4px' }}>
            {loading ? 'Saving...' : 'Record Payment'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

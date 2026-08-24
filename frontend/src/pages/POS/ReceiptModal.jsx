import React from 'react';
import styles from './ReceiptModal.module.css';

const ReceiptModal = ({ receipt, onClose }) => {
  const handlePrint = () => {
    window.print();
  };

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString();
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.receiptContent} id="printable-receipt">
          <div className={styles.header}>
            <h2>{receipt.company?.name || 'Store'}</h2>
            <p>{receipt.company?.address || ''}</p>
            {receipt.company?.gstin && <p>GSTIN: {receipt.company.gstin}</p>}
            {receipt.company?.phone && <p>Ph: {receipt.company.phone}</p>}
          </div>

          <div className={styles.divider}></div>

          <div className={styles.row}>
            <span>Bill No:</span>
            <span className={styles.bold}>{receipt.bill_number}</span>
          </div>
          <div className={styles.row}>
            <span>Date:</span>
            <span>{formatDate(receipt.sale_date)}</span>
          </div>
          {receipt.customer?.name && (
            <div className={styles.row}>
              <span>Customer:</span>
              <span>{receipt.customer?.name}</span>
            </div>
          )}

          <div className={styles.divider}></div>

          <table className={styles.itemsTable}>
            <thead>
              <tr>
                <th>Item</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {receipt.items.map((item, idx) => (
                <tr key={idx}>
                  <td>
                    {item.sku}
                    <div style={{fontSize: '10px', color: '#666'}}>GST {item.gst_rate}%</div>
                  </td>
                  <td>{item.quantity}</td>
                  <td>{(item.rate || 0).toFixed(2)}</td>
                  <td>{(item.line_total || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className={styles.divider}></div>

          <div className={styles.row}>
            <span>Taxable Amount:</span>
            <span>₹{(receipt.totals?.taxable_amount || 0).toFixed(2)}</span>
          </div>
          <div className={styles.row}>
            <span>Total Tax (GST):</span>
            <span>₹{(receipt.totals?.total_tax || 0).toFixed(2)}</span>
          </div>
          <div className={`${styles.row} ${styles.bold}`} style={{fontSize: '18px', marginTop: '8px'}}>
            <span>Grand Total:</span>
            <span>₹{(receipt.totals?.grand_total || 0).toFixed(2)}</span>
          </div>

          <div className={styles.divider}></div>
          
          <div className={styles.row}>
            <span>Payment Method:</span>
            <span>{receipt.payment_method}</span>
          </div>

          <div className={styles.footer}>
            Thank you for shopping with us!
          </div>
        </div>
        
        <div className={styles.actions}>
          <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={onClose}>
            Close
          </button>
          <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={handlePrint}>
            Print Receipt
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReceiptModal;

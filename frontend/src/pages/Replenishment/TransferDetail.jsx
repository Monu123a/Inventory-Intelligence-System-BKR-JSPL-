import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import styles from './TransferDetail.module.css';

const TransferDetail = () => {
  const { transferId } = useParams();
  const navigate = useNavigate();
  const [transfer, setTransfer] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock API call
    setTimeout(() => {
      setTransfer({
        id: transferId,
        from: 'Main Warehouse',
        to: 'Store A',
        status: 'Pending Approval',
        createdDate: '2023-10-02',
        dispatchDate: '-',
        value: 3400,
        items: [
          { id: 1, sku: 'SKU-001', name: 'Widget A', qty: 10, price: 120 },
          { id: 2, sku: 'SKU-002', name: 'Widget B', qty: 20, price: 110 }
        ]
      });
      setLoading(false);
    }, 500);
  }, [transferId]);

  const handleQtyChange = (itemId, newQty) => {
    if (transfer.status !== 'Pending Approval') return;
    setTransfer({
      ...transfer,
      items: transfer.items.map(item => item.id === itemId ? { ...item, qty: Number(newQty) } : item)
    });
  };

  const updateStatus = (newStatus) => {
    setTransfer({ ...transfer, status: newStatus });
    alert(`Status updated to ${newStatus}`);
  };

  const renderActionButtons = () => {
    switch (transfer.status) {
      case 'Pending Approval':
        return <button className={styles.primaryBtn} onClick={() => updateStatus('Completed')}>Approve</button>;
      default:
        return null;
    }
  };

  if (loading) return <div className={styles.loading}>Loading Transfer Details...</div>;
  if (!transfer) return <div className={styles.loading}>Transfer not found.</div>;

  const isEditable = transfer.status === 'Pending Approval';

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <button className={styles.backBtn} onClick={() => navigate(-1)}>&larr; Back</button>
          <h1>Transfer Details: {transfer.id}</h1>
          <span className={styles.badge}>{transfer.status}</span>
        </div>
        <div className={styles.actions}>
          {renderActionButtons()}
        </div>
      </div>

      <div className={styles.infoCard}>
        <div className={styles.infoRow}>
          <div>
            <span className={styles.infoLabel}>From</span>
            <div className={styles.infoValue}>{transfer.from}</div>
          </div>
          <div>
            <span className={styles.infoLabel}>To</span>
            <div className={styles.infoValue}>{transfer.to}</div>
          </div>
          <div>
            <span className={styles.infoLabel}>Created Date</span>
            <div className={styles.infoValue}>{transfer.createdDate}</div>
          </div>
          <div>
            <span className={styles.infoLabel}>Dispatch Date</span>
            <div className={styles.infoValue}>{transfer.dispatchDate}</div>
          </div>
          <div>
            <span className={styles.infoLabel}>Total Value</span>
            <div className={styles.infoValue}>₹{transfer.value.toFixed(2)}</div>
          </div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <h2>Transfer Items</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Product Name</th>
              <th>Unit Price</th>
              <th>Quantity</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {transfer.items.map((item) => (
              <tr key={item.id}>
                <td>{item.sku}</td>
                <td>{item.name}</td>
                <td>₹{item.price.toFixed(2)}</td>
                <td>
                  {isEditable ? (
                    <input 
                      type="number" 
                      className={styles.qtyInput} 
                      value={item.qty} 
                      onChange={(e) => handleQtyChange(item.id, e.target.value)}
                      min="1"
                    />
                  ) : (
                    item.qty
                  )}
                </td>
                <td>₹{(item.qty * item.price).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TransferDetail;

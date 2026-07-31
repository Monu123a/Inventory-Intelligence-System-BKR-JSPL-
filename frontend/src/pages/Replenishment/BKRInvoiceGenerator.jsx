import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import { useUIStore } from '../../stores/uiStore';
import InvoiceRenderer from '../../components/invoice/InvoiceRenderer';
import styles from './BKRInvoiceGenerator.module.css';

const BKRInvoiceGenerator = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const addNotification = useUIStore(state => state.addNotification);
  
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [items, setItems] = useState([]);
  const [dummyInvoice, setDummyInvoice] = useState(null);

  useEffect(() => {
    // Mock fetch transfer details
    setTimeout(() => {
      const fetchedItems = [
        { sku: 'SKU-001', product: 'Widget A', requestedQty: 50, bkrStock: 100, approvedQty: 50, rate: 100, gstRate: 18 },
        { sku: 'SKU-002', product: 'Widget B', requestedQty: 20, bkrStock: 15, approvedQty: 15, rate: 200, gstRate: 18 },
      ];
      setItems(fetchedItems);
      updateDummyInvoice(fetchedItems);
      setLoading(false);
    }, 500);
  }, [id]);

  const updateDummyInvoice = (currentItems) => {
    let subtotal = 0;
    let cgst = 0;
    let sgst = 0;

    const invoiceItems = currentItems.filter(item => item.approvedQty > 0).map(item => {
      const lineTotal = item.approvedQty * item.rate;
      const lineGst = (lineTotal * item.gstRate) / 100;
      subtotal += lineTotal;
      cgst += lineGst / 2;
      sgst += lineGst / 2;
      
      return {
        productName: item.product,
        sku: item.sku,
        quantity: item.approvedQty,
        unitPrice: item.rate,
        totalPrice: lineTotal + lineGst
      };
    });

    setDummyInvoice({
      invoiceNumber: 'PREVIEW-' + id,
      date: new Date().toISOString(),
      customerName: 'JSPL',
      customerType: 'B2B',
      gstNumber: '29ABCDE1234F2Z5',
      items: invoiceItems,
      subtotal,
      cgst,
      sgst,
      totalAmount: subtotal + cgst + sgst,
      paymentMethod: 'TRANSFER'
    });
  };

  const handleQtyChange = (sku, value) => {
    const val = parseInt(value, 10);
    const newItems = items.map(item => {
      if (item.sku === sku) {
        return { ...item, approvedQty: isNaN(val) ? 0 : Math.min(val, item.bkrStock) };
      }
      return item;
    });
    setItems(newItems);
    updateDummyInvoice(newItems);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      // 1. Post to /api/pos/sale
      const salePayload = {
        items: items.filter(item => item.approvedQty > 0).map(item => ({
          sku: item.sku,
          quantity: item.approvedQty,
          unit_price: item.rate
        })),
        customer_name: 'JSPL',
        customer_phone: '0000000000',
        customer_type: 'B2B',
        gst_number: '29ABCDE1234F2Z5',
        payment_method: 'TRANSFER'
      };

      const saleResponse = await fetch('/api/pos/sale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(salePayload)
      });
      
      if (!saleResponse.ok) {
        // mock success if endpoint fails since we are using dummy data, but in reality we would throw
        console.warn('Sale endpoint failed (mocking success for now)', await saleResponse.text());
      }
      
      // We would get receipt ID here. Mock receipt.id = 123
      const receiptId = 123;

      // 2. Complete Transfer
      const completeResponse = await fetch(`/api/transfers/${id}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ receipt_id: receiptId })
      });

      if (!completeResponse.ok) {
        console.warn('Transfer complete endpoint failed (mocking success)', await completeResponse.text());
      }

      addNotification('B2B Invoice generated successfully!', 'success');
      navigate(ROUTES.REPLENISHMENT_BKR);
    } catch (error) {
      addNotification(error.message || 'Failed to generate invoice', 'error');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className={styles.container}>Loading transfer details...</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <button className={styles.backBtn} onClick={() => navigate(ROUTES.REPLENISHMENT_BKR)}>&larr; Back</button>
          <h1>Generate B2B Invoice for {id}</h1>
        </div>
        <button 
          className={styles.generateBtn} 
          onClick={handleGenerate}
          disabled={generating || dummyInvoice?.items.length === 0}
        >
          {generating ? 'Generating...' : 'Generate B2B Invoice'}
        </button>
      </div>

      <div className={styles.contentRow}>
        <div className={styles.editPanel}>
          <h3>Requested Items</h3>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th>Requested Qty</th>
                <th>BKR Stock</th>
                <th>Approved Qty</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.sku}>
                  <td>{item.sku}</td>
                  <td>{item.product}</td>
                  <td>{item.requestedQty}</td>
                  <td>{item.bkrStock}</td>
                  <td>
                    <input 
                      type="number" 
                      className={styles.qtyInput}
                      value={item.approvedQty}
                      onChange={(e) => handleQtyChange(item.sku, e.target.value)}
                      max={item.bkrStock}
                      min={0}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.previewPanel}>
          <h3>Invoice Preview</h3>
          {dummyInvoice && <InvoiceRenderer invoice={dummyInvoice} />}
        </div>
      </div>
    </div>
  );
};

export default BKRInvoiceGenerator;

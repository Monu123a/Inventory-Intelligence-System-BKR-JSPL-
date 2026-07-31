import React, { useState, useEffect, useRef } from 'react';
import api from '../../services/api';
import styles from './POSPage.module.css';
import { FiX } from 'react-icons/fi';
import ReceiptModal from './ReceiptModal';

const POSPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [cart, setCart] = useState([]);
  const [customerInfo, setCustomerInfo] = useState({ name: '', mobile: '' });
  const [paymentMethod, setPaymentMethod] = useState('Cash');
  const [error, setError] = useState('');
  const [receiptData, setReceiptData] = useState(null);
  
  const searchTimeout = useRef(null);

  // Search effect
  useEffect(() => {
    if (searchTerm.length < 2) {
      setSearchResults([]);
      return;
    }

    if (searchTimeout.current) clearTimeout(searchTimeout.current);

    searchTimeout.current = setTimeout(async () => {
      try {
        const response = await api.get(`/api/pos/products/search?q=${encodeURIComponent(searchTerm)}`);
        setSearchResults(response.data);
      } catch (err) {
        console.error("Search failed", err);
      }
    }, 300);

    return () => clearTimeout(searchTimeout.current);
  }, [searchTerm]);

  const addToCart = (product) => {
    setSearchResults([]);
    setSearchTerm('');
    
    // Check if already in cart
    const existingIndex = cart.findIndex(item => item.product_id === product.id);
    if (existingIndex >= 0) {
      updateCartItem(existingIndex, 'quantity', cart[existingIndex].quantity + 1);
      return;
    }

    // Determine GST rate: default to 0 if null to trigger warning
    const initialGst = product.default_gst_rate !== null ? product.default_gst_rate : 0;
    const initialPrice = product.default_price || 0;

    const newItem = {
      product_id: product.id,
      sku: product.sku,
      name: product.name,
      available_stock: product.available_stock,
      quantity: 1,
      selling_price: initialPrice,
      gst_rate: initialGst,
      gst_needs_confirmation: product.default_gst_rate === null,
      taxable_amount: initialPrice,
      cgst: (initialPrice * (initialGst / 100)) / 2,
      sgst: (initialPrice * (initialGst / 100)) / 2,
      line_total: initialPrice + (initialPrice * (initialGst / 100))
    };

    setCart([...cart, newItem]);
  };

  const removeFromCart = (index) => {
    const newCart = [...cart];
    newCart.splice(index, 1);
    setCart(newCart);
  };

  const updateCartItem = (index, field, value) => {
    const newCart = [...cart];
    const item = { ...newCart[index] };
    
    // Parse values
    if (field === 'quantity') item.quantity = parseInt(value) || 0;
    if (field === 'selling_price') item.selling_price = parseFloat(value) || 0;
    if (field === 'gst_rate') {
      item.gst_rate = parseFloat(value) || 0;
      item.gst_needs_confirmation = false; // Confirmed by editing
    }
    
    // Validate stock
    if (field === 'quantity' && item.quantity > item.available_stock) {
      item.quantity = item.available_stock;
      setError(`Cannot exceed available stock (${item.available_stock}) for ${item.sku}`);
      setTimeout(() => setError(''), 3000);
    }

    // Recalculate taxes
    item.taxable_amount = item.quantity * item.selling_price;
    const gstAmount = item.taxable_amount * (item.gst_rate / 100);
    item.cgst = gstAmount / 2;
    item.sgst = gstAmount / 2;
    item.line_total = item.taxable_amount + gstAmount;

    newCart[index] = item;
    setCart(newCart);
  };

  // Calculate Totals
  const totals = cart.reduce((acc, item) => {
    acc.taxable += item.taxable_amount;
    acc.cgst += item.cgst;
    acc.sgst += item.sgst;
    acc.tax += item.cgst + item.sgst;
    acc.grand += item.line_total;
    return acc;
  }, { taxable: 0, cgst: 0, sgst: 0, tax: 0, grand: 0 });

  const hasUnconfirmedGst = cart.some(item => item.gst_needs_confirmation);

  const handleCheckout = async () => {
    if (cart.length === 0) return;
    if (hasUnconfirmedGst) {
      setError("Please confirm the 0% GST rate for highlighted items.");
      return;
    }
    
    setError('');
    
    try {
      const payload = {
        customer_name: customerInfo.name || null,
        customer_mobile: customerInfo.mobile || null,
        payment_method: paymentMethod,
        total_taxable_amount: totals.taxable,
        total_tax: totals.tax,
        grand_total: totals.grand,
        items: cart
      };

      const res = await api.post('/api/pos/sale', payload);
      setReceiptData(res.data.receipt);
      setCart([]);
      setCustomerInfo({ name: '', mobile: '' });
      setSearchTerm('');
    } catch (err) {
      setError(err.response?.data?.detail || "Checkout failed");
    }
  };

  return (
    <div className={styles.posContainer}>
      <div className={styles.header}>
        <h1>Offline POS (BKR)</h1>
      </div>

      {error && <div className={styles.errorMsg}>{error}</div>}

      <div className={styles.layout}>
        <div className={styles.mainPanel}>
          <h2 className={styles.sectionTitle}>Customer Details (Optional)</h2>
          <div className={styles.customerForm}>
            <div className={styles.inputGroup}>
              <label>Customer Name</label>
              <input 
                value={customerInfo.name} 
                onChange={(e) => setCustomerInfo({...customerInfo, name: e.target.value})}
                placeholder="Enter name"
              />
            </div>
            <div className={styles.inputGroup}>
              <label>Mobile Number</label>
              <input 
                value={customerInfo.mobile} 
                onChange={(e) => setCustomerInfo({...customerInfo, mobile: e.target.value})}
                placeholder="Enter mobile"
              />
            </div>
          </div>

          <h2 className={styles.sectionTitle}>Add Products</h2>
          <div className={styles.searchContainer}>
            <input 
              className={styles.searchInput}
              placeholder="Search by SKU or Name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchResults.length > 0 && (
              <div className={styles.searchResults}>
                {searchResults.map(result => (
                  <div key={result.id} className={styles.searchItem} onClick={() => addToCart(result)}>
                    <div className={styles.searchItemMain}>
                      <span className={styles.itemName}>{result.sku} - {result.name}</span>
                      <span className={styles.itemMeta}>Brand: {result.brand} | Cat: {result.category}</span>
                    </div>
                    <div className={`${styles.itemStock} ${result.available_stock < 5 ? styles.low : ''}`}>
                      Stock: {result.available_stock}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <table className={styles.cartTable}>
            <thead>
              <tr>
                <th>Product</th>
                <th>Qty</th>
                <th>Price (₹)</th>
                <th>GST %</th>
                <th>Taxable</th>
                <th>Total (₹)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cart.map((item, index) => (
                <tr key={`${item.sku}-${index}`}>
                  <td>
                    <div className={styles.itemName}>{item.sku}</div>
                    <div className={styles.itemMeta}>{item.name}</div>
                  </td>
                  <td>
                    <input 
                      type="number" 
                      className={styles.qtyInput} 
                      value={item.quantity} 
                      onChange={(e) => updateCartItem(index, 'quantity', e.target.value)}
                      min="1"
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      className={styles.priceInput} 
                      value={item.selling_price} 
                      onChange={(e) => updateCartItem(index, 'selling_price', e.target.value)}
                      step="0.01"
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      className={`${styles.gstInput} ${item.gst_needs_confirmation ? styles.gstWarning : ''}`} 
                      value={item.gst_rate} 
                      onChange={(e) => updateCartItem(index, 'gst_rate', e.target.value)}
                      step="0.1"
                    />
                  </td>
                  <td>₹{item.taxable_amount.toFixed(2)}</td>
                  <td>₹{item.line_total.toFixed(2)}</td>
                  <td>
                    <button className={styles.removeBtn} onClick={() => removeFromCart(index)}>
                      <FiX />
                    </button>
                  </td>
                </tr>
              ))}
              {cart.length === 0 && (
                <tr>
                  <td colSpan="7" style={{textAlign: 'center', padding: '24px', color: '#666'}}>
                    Cart is empty. Search products to add.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className={styles.summaryPanel}>
          <h2 className={styles.sectionTitle}>Bill Summary</h2>
          
          <div className={styles.inputGroup} style={{marginBottom: '24px'}}>
            <label>Payment Method</label>
            <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              <option value="Cash">Cash</option>
              <option value="UPI">UPI</option>
              <option value="Card">Card</option>
            </select>
          </div>

          <div className={styles.summaryRow}>
            <span>Taxable Amount</span>
            <span>₹{totals.taxable.toFixed(2)}</span>
          </div>
          <div className={styles.summaryRow}>
            <span>CGST</span>
            <span>₹{totals.cgst.toFixed(2)}</span>
          </div>
          <div className={styles.summaryRow}>
            <span>SGST</span>
            <span>₹{totals.sgst.toFixed(2)}</span>
          </div>
          <div className={`${styles.summaryRow} ${styles.total}`}>
            <span>Grand Total</span>
            <span>₹{totals.grand.toFixed(2)}</span>
          </div>

          <button 
            className={styles.checkoutBtn} 
            disabled={cart.length === 0 || hasUnconfirmedGst}
            onClick={handleCheckout}
          >
            {hasUnconfirmedGst ? "Confirm GST Rates" : "Complete Sale"}
          </button>
        </div>
      </div>

      {receiptData && (
        <ReceiptModal receipt={receiptData} onClose={() => setReceiptData(null)} />
      )}
    </div>
  );
};

export default POSPage;

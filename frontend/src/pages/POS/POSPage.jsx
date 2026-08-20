import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { posService } from '../../services/pos';
import { handleApiError } from '../../utils/errorHandler';
import styles from './POSPage.module.css';
import ReceiptModal from './ReceiptModal';
import { FiX, FiChevronDown, FiChevronUp } from 'react-icons/fi';

// ---------------------------------------------------------------------------
// GSTIN validation (basic format: 2-digit state + 10 PAN + 1 entity + 1 Z + 1 check)
// ---------------------------------------------------------------------------
const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

function validateGstin(gstin) {
  if (!gstin) return null;
  const cleaned = gstin.trim().toUpperCase();
  if (!GSTIN_REGEX.test(cleaned)) return 'Invalid GSTIN format';
  return null;
}

function gstinStateCode(gstin) {
  if (!gstin || gstin.length < 2) return '';
  return gstin.substring(0, 2);
}

// ---------------------------------------------------------------------------
// Indian States lookup for Place of Supply
// ---------------------------------------------------------------------------
const INDIAN_STATES = [
  { code: '01', name: 'Jammu & Kashmir' }, { code: '02', name: 'Himachal Pradesh' },
  { code: '03', name: 'Punjab' }, { code: '04', name: 'Chandigarh' },
  { code: '05', name: 'Uttarakhand' }, { code: '06', name: 'Haryana' },
  { code: '07', name: 'Delhi' }, { code: '08', name: 'Rajasthan' },
  { code: '09', name: 'Uttar Pradesh' }, { code: '10', name: 'Bihar' },
  { code: '11', name: 'Sikkim' }, { code: '12', name: 'Arunachal Pradesh' },
  { code: '13', name: 'Nagaland' }, { code: '14', name: 'Manipur' },
  { code: '15', name: 'Mizoram' }, { code: '16', name: 'Tripura' },
  { code: '17', name: 'Meghalaya' }, { code: '18', name: 'Assam' },
  { code: '19', name: 'West Bengal' }, { code: '20', name: 'Jharkhand' },
  { code: '21', name: 'Odisha' }, { code: '22', name: 'Chhattisgarh' },
  { code: '23', name: 'Madhya Pradesh' }, { code: '24', name: 'Gujarat' },
  { code: '27', name: 'Maharashtra' }, { code: '29', name: 'Karnataka' },
  { code: '30', name: 'Goa' }, { code: '32', name: 'Kerala' },
  { code: '33', name: 'Tamil Nadu' }, { code: '34', name: 'Puducherry' },
  { code: '36', name: 'Telangana' }, { code: '37', name: 'Andhra Pradesh' },
];

// ---------------------------------------------------------------------------
// Collapsible Section component
// ---------------------------------------------------------------------------
const CollapsibleSection = ({ title, defaultOpen = false, children }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={styles.collapsibleSection}>
      <button type="button" className={styles.collapsibleHeader} onClick={() => setOpen(!open)}>
        <span>{title}</span>
        {open ? <FiChevronUp /> : <FiChevronDown />}
      </button>
      {open && <div className={styles.collapsibleBody}>{children}</div>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// POSPage Component
// ---------------------------------------------------------------------------
const POSPage = () => {
  const navigate = useNavigate();

  // Existing state
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [cart, setCart] = useState([]);
  const [paymentMethod, setPaymentMethod] = useState('Cash');
  const [paymentReference, setPaymentReference] = useState('');
  const [error, setError] = useState('');
  const [completedReceipt, setCompletedReceipt] = useState(null);

  const idempotencyKeyRef = useRef(window.crypto.randomUUID());

  const queryClient = useQueryClient();

  // New: Invoice Type
  const [invoiceType, setInvoiceType] = useState('B2C');

  // New: Extended Customer Info
  const [customerInfo, setCustomerInfo] = useState({
    name: '', mobile: '', gstin: '', address: '',
    state: '', state_code: '', place_of_supply: '',
    email: '', phone: '',
  });

  // New: Invoice Info
  const [invoiceInfo, setInvoiceInfo] = useState({
    payment_terms: '', delivery_note: '', delivery_note_date: '',
    dispatch_document_number: '', dispatch_through: '',
    destination: '', vehicle_number: '', lr_rr_number: '',
    terms_of_delivery: '',
  });

  // GSTIN validation state
  const [gstinError, setGstinError] = useState('');

  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchTerm(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data: searchData } = useQuery({
    queryKey: ['posSearch', debouncedSearchTerm],
    queryFn: () => posService.searchProducts(debouncedSearchTerm),
    enabled: debouncedSearchTerm.length >= 2,
  });

  useEffect(() => {
    if (debouncedSearchTerm.length >= 2 && searchData) {
      setSearchResults(searchData);
    } else {
      setSearchResults([]);
    }
  }, [searchData, debouncedSearchTerm]);

  // Determine if inter-state (IGST) or intra-state (CGST+SGST)
  // Compare company state code with place of supply state code
  const companyStateCode = '27'; // Default BKR state code (Maharashtra) — will come from settings later
  const isInterState = customerInfo.place_of_supply &&
    customerInfo.place_of_supply !== '' &&
    (() => {
      const found = INDIAN_STATES.find(s => s.name === customerInfo.place_of_supply);
      return found ? found.code !== companyStateCode : false;
    })();

  // ---------------------------------------------------------------------------
  // GSTIN auto-fill state code when GSTIN changes
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (customerInfo.gstin && customerInfo.gstin.length >= 2) {
      const err = validateGstin(customerInfo.gstin);
      setGstinError(err || '');
      if (!err) {
        const sc = gstinStateCode(customerInfo.gstin);
        const state = INDIAN_STATES.find(s => s.code === sc);
        if (state) {
          setCustomerInfo(prev => ({
            ...prev,
            state_code: sc,
            state: state.name,
            place_of_supply: prev.place_of_supply || state.name,
          }));
        }
      }
    } else {
      setGstinError('');
    }
  }, [customerInfo.gstin]);

  // ---------------------------------------------------------------------------
  // Cart operations (preserved + extended with discount, HSN, unit, IGST)
  // ---------------------------------------------------------------------------
  const addToCart = (product) => {
    setSearchResults([]);
    setSearchTerm('');

    const existingIndex = cart.findIndex(item => item.product_id === product.id);
    if (existingIndex >= 0) {
      updateCartItem(existingIndex, 'quantity', cart[existingIndex].quantity + 1);
      return;
    }

    const initialGst = product.default_gst_rate !== null ? product.default_gst_rate : 0;
    const initialPrice = product.default_price || 0;
    const taxable = initialPrice * 1;
    const gstAmount = taxable * (initialGst / 100);

    const newItem = {
      product_id: product.id,
      sku: product.sku,
      product_name: product.name,
      name: product.name,
      hsn_sac: product.hsn_sac || '',
      unit: product.unit || 'PCS',
      available_stock: product.available_stock,
      quantity: 1,
      selling_price: initialPrice,
      discount: 0,
      gst_rate: initialGst,
      gst_needs_confirmation: product.default_gst_rate === null,
      taxable_amount: taxable,
      cgst: isInterState ? 0 : gstAmount / 2,
      sgst: isInterState ? 0 : gstAmount / 2,
      igst: isInterState ? gstAmount : 0,
      line_total: taxable + gstAmount,
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

    if (field === 'quantity') item.quantity = parseInt(value) || 0;
    if (field === 'selling_price') item.selling_price = parseFloat(value) || 0;
    if (field === 'discount') item.discount = parseFloat(value) || 0;
    if (field === 'gst_rate') {
      item.gst_rate = parseFloat(value) || 0;
      item.gst_needs_confirmation = false;
    }

    // Validate stock
    if (field === 'quantity' && item.quantity > item.available_stock) {
      item.quantity = item.available_stock;
      setError(`Cannot exceed available stock (${item.available_stock}) for ${item.sku}`);
      setTimeout(() => setError(''), 3000);
    }

    // Recalculate: taxable = (price * qty) - discount
    const grossAmount = item.quantity * item.selling_price;
    item.taxable_amount = Math.max(0, grossAmount - item.discount);
    const gstAmount = item.taxable_amount * (item.gst_rate / 100);
    item.cgst = isInterState ? 0 : gstAmount / 2;
    item.sgst = isInterState ? 0 : gstAmount / 2;
    item.igst = isInterState ? gstAmount : 0;
    item.line_total = item.taxable_amount + gstAmount;

    newCart[index] = item;
    setCart(newCart);
  };

  // Recalculate all items when inter-state status changes
  useEffect(() => {
    if (cart.length === 0) return;
    setCart(prev => prev.map(item => {
      const grossAmount = item.quantity * item.selling_price;
      const taxable = Math.max(0, grossAmount - item.discount);
      const gstAmount = taxable * (item.gst_rate / 100);
      return {
        ...item,
        taxable_amount: taxable,
        cgst: isInterState ? 0 : gstAmount / 2,
        sgst: isInterState ? 0 : gstAmount / 2,
        igst: isInterState ? gstAmount : 0,
        line_total: taxable + gstAmount,
      };
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isInterState]);

  // ---------------------------------------------------------------------------
  // Totals (extended with IGST)
  // ---------------------------------------------------------------------------
  const totals = cart.reduce((acc, item) => {
    acc.taxable += item.taxable_amount;
    acc.cgst += item.cgst;
    acc.sgst += item.sgst;
    acc.igst += item.igst;
    acc.tax += item.cgst + item.sgst + item.igst;
    acc.grand += item.line_total;
    return acc;
  }, { taxable: 0, cgst: 0, sgst: 0, igst: 0, tax: 0, grand: 0 });

  const hasUnconfirmedGst = cart.some(item => item.gst_needs_confirmation);

  // ---------------------------------------------------------------------------
  // Checkout Mutation
  // ---------------------------------------------------------------------------
  const checkoutMutation = useMutation({
    mutationFn: posService.checkout,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      
      const receipt = data.receipt;
      const saleId = receipt?.id;

      // Reset form
      setCart([]);
      setCustomerInfo({ name: '', mobile: '', gstin: '', address: '', state: '', state_code: '', place_of_supply: '', email: '', phone: '' });
      setInvoiceInfo({ payment_terms: '', delivery_note: '', delivery_note_date: '', dispatch_document_number: '', dispatch_through: '', destination: '', vehicle_number: '', lr_rr_number: '', terms_of_delivery: '' });
      setPaymentReference('');
      setSearchTerm('');
      
      // Regenerate idempotency key for the next operation
      idempotencyKeyRef.current = window.crypto.randomUUID();

      if (!receipt?.id) return;

      if (invoiceType === 'B2B') {
        navigate(`/sales/${saleId}/invoice`, { state: { receipt } });
      } else {
        setCompletedReceipt(receipt);
      }
    },
    onError: (err) => {
      handleApiError(err, "Checkout failed");
    }
  });

  const handleCheckout = () => {
    if (cart.length === 0) return;
    if (hasUnconfirmedGst) {
      setError("Please confirm the 0% GST rate for highlighted items.");
      return;
    }

    // B2B validation: GSTIN is required
    if (invoiceType === 'B2B') {
      if (!customerInfo.gstin) {
        setError("GSTIN is required for B2B invoices.");
        return;
      }
      const gstErr = validateGstin(customerInfo.gstin);
      if (gstErr) {
        setError(`GSTIN Error: ${gstErr}`);
        return;
      }
      if (!customerInfo.name) {
        setError("Customer name is required for B2B invoices.");
        return;
      }
      if (!customerInfo.state || !customerInfo.place_of_supply) {
        setError("State and Place of Supply are required for B2B invoices.");
        return;
      }
    }

    setError('');

    const payload = {
      idempotency_key: idempotencyKeyRef.current,
      invoice_type: invoiceType,
      customer_name: customerInfo.name || null,
      customer_mobile: customerInfo.mobile || null,
      customer_gstin: customerInfo.gstin || null,
      customer_address: customerInfo.address || null,
      customer_state: customerInfo.state || null,
      customer_state_code: customerInfo.state_code || null,
      place_of_supply: customerInfo.place_of_supply || null,
      customer_email: customerInfo.email || null,
      customer_phone: customerInfo.phone || null,

      payment_terms: invoiceInfo.payment_terms || null,
      delivery_note: invoiceInfo.delivery_note || null,
      delivery_note_date: invoiceInfo.delivery_note_date || null,
      dispatch_document_number: invoiceInfo.dispatch_document_number || null,
      dispatch_through: invoiceInfo.dispatch_through || null,
      destination: invoiceInfo.destination || null,
      vehicle_number: invoiceInfo.vehicle_number || null,
      lr_rr_number: invoiceInfo.lr_rr_number || null,
      terms_of_delivery: invoiceInfo.terms_of_delivery || null,

      payment_method: paymentMethod,
      payment_reference: paymentReference || null,
      total_taxable_amount: totals.taxable,
      total_tax: totals.tax,
      grand_total: totals.grand,
      items: cart.map(item => ({
        product_id: item.product_id,
        sku: item.sku,
        product_name: item.product_name || item.name,
        hsn_sac: item.hsn_sac || null,
        unit: item.unit || null,
        quantity: item.quantity,
        selling_price: item.selling_price,
        discount: item.discount,
        gst_rate: item.gst_rate,
        taxable_amount: item.taxable_amount,
        cgst: item.cgst,
        sgst: item.sgst,
        igst: item.igst,
        line_total: item.line_total,
      })),
    };

    checkoutMutation.mutate(payload);
  };

  // Helper to update nested state
  const updateCustomer = (field, value) => setCustomerInfo(prev => ({ ...prev, [field]: value }));
  const updateInvoice = (field, value) => setInvoiceInfo(prev => ({ ...prev, [field]: value }));

  return (
    <div className={styles.posContainer}>
      <div className={styles.header}>
        <h1>Offline POS (BKR)</h1>
        {/* Invoice Type Selector */}
        <div className={styles.invoiceTypeSelector}>
          <label>Invoice Type</label>
          <div className={styles.invoiceTypeBtns}>
            <button
              type="button"
              className={`${styles.typeBtn} ${invoiceType === 'B2C' ? styles.typeBtnActive : ''}`}
              onClick={() => setInvoiceType('B2C')}
            >
              B2C
            </button>
            <button
              type="button"
              className={`${styles.typeBtn} ${invoiceType === 'B2B' ? styles.typeBtnActive : ''}`}
              onClick={() => setInvoiceType('B2B')}
            >
              B2B
            </button>
          </div>
        </div>
      </div>

      {error && <div className={styles.errorMsg}>{error}</div>}

      <div className={styles.layout}>
        <div className={styles.mainPanel}>
          {/* Customer Details - expanded for B2B */}
          <div className={styles.sectionBlock}>
            <h2 className={styles.sectionTitle}>Customer Details{invoiceType === 'B2B' ? ' (Required for B2B)' : ' (Optional)'}</h2>
            <div className={styles.formGrid}>
              <div className={styles.inputGroup}>
                <label>Customer Name {invoiceType === 'B2B' && <span className={styles.required}>*</span>}</label>
                <input value={customerInfo.name} onChange={e => updateCustomer('name', e.target.value)} placeholder="Enter name" />
              </div>
              <div className={styles.inputGroup}>
                <label>Mobile Number</label>
                <input value={customerInfo.mobile} onChange={e => updateCustomer('mobile', e.target.value)} placeholder="Enter mobile" />
              </div>
              <div className={styles.inputGroup}>
                <label>GSTIN {invoiceType === 'B2B' && <span className={styles.required}>*</span>}</label>
                <input
                  value={customerInfo.gstin}
                  onChange={e => updateCustomer('gstin', e.target.value.toUpperCase())}
                  placeholder="e.g. 27AAAAA0000A1Z5"
                  className={gstinError ? styles.inputError : ''}
                  maxLength={15}
                />
                {gstinError && <span className={styles.fieldError}>{gstinError}</span>}
              </div>
              <div className={styles.inputGroup}>
                <label>Email</label>
                <input value={customerInfo.email} onChange={e => updateCustomer('email', e.target.value)} placeholder="Email" type="email" />
              </div>
              <div className={`${styles.inputGroup} ${styles.fullWidth}`}>
                <label>Address</label>
                <input value={customerInfo.address} onChange={e => updateCustomer('address', e.target.value)} placeholder="Full address" />
              </div>
              <div className={styles.inputGroup}>
                <label>State</label>
                <select value={customerInfo.state} onChange={e => {
                  const st = INDIAN_STATES.find(s => s.name === e.target.value);
                  updateCustomer('state', e.target.value);
                  if (st) updateCustomer('state_code', st.code);
                }}>
                  <option value="">Select State</option>
                  {INDIAN_STATES.map(s => <option key={s.code} value={s.name}>{s.name}</option>)}
                </select>
              </div>
              <div className={styles.inputGroup}>
                <label>State Code</label>
                <input value={customerInfo.state_code} onChange={e => updateCustomer('state_code', e.target.value)} placeholder="e.g. 27" readOnly={!!customerInfo.state} />
              </div>
              <div className={styles.inputGroup}>
                <label>Place of Supply</label>
                <select value={customerInfo.place_of_supply} onChange={e => updateCustomer('place_of_supply', e.target.value)}>
                  <option value="">Select Place of Supply</option>
                  {INDIAN_STATES.map(s => <option key={s.code} value={s.name}>{s.name}</option>)}
                </select>
              </div>
              <div className={styles.inputGroup}>
                <label>Phone</label>
                <input value={customerInfo.phone} onChange={e => updateCustomer('phone', e.target.value)} placeholder="Phone number" />
              </div>
            </div>
          </div>

          {/* Invoice & Transport Details */}
          <CollapsibleSection title="Invoice & Transport Details">
            <div className={styles.formGrid}>
              <div className={styles.inputGroup}>
                <label>Payment Terms</label>
                <input value={invoiceInfo.payment_terms} onChange={e => updateInvoice('payment_terms', e.target.value)} placeholder="e.g. Net 30" />
              </div>
              <div className={styles.inputGroup}>
                <label>Delivery Note</label>
                <input value={invoiceInfo.delivery_note} onChange={e => updateInvoice('delivery_note', e.target.value)} placeholder="Delivery note" />
              </div>
              <div className={styles.inputGroup}>
                <label>Delivery Note Date</label>
                <input type="date" value={invoiceInfo.delivery_note_date} onChange={e => updateInvoice('delivery_note_date', e.target.value)} />
              </div>
              <div className={styles.inputGroup}>
                <label>Dispatch Doc No.</label>
                <input value={invoiceInfo.dispatch_document_number} onChange={e => updateInvoice('dispatch_document_number', e.target.value)} placeholder="Document number" />
              </div>
              <div className={styles.inputGroup}>
                <label>Dispatch Through</label>
                <input value={invoiceInfo.dispatch_through} onChange={e => updateInvoice('dispatch_through', e.target.value)} placeholder="e.g. Courier" />
              </div>
              <div className={styles.inputGroup}>
                <label>Destination</label>
                <input value={invoiceInfo.destination} onChange={e => updateInvoice('destination', e.target.value)} placeholder="Destination city" />
              </div>
              <div className={styles.inputGroup}>
                <label>Vehicle Number</label>
                <input value={invoiceInfo.vehicle_number} onChange={e => updateInvoice('vehicle_number', e.target.value)} placeholder="e.g. MH01AB1234" />
              </div>
              <div className={styles.inputGroup}>
                <label>LR/RR Number</label>
                <input value={invoiceInfo.lr_rr_number} onChange={e => updateInvoice('lr_rr_number', e.target.value)} placeholder="LR/RR number" />
              </div>
              <div className={styles.inputGroup}>
                <label>Terms of Delivery</label>
                <input value={invoiceInfo.terms_of_delivery} onChange={e => updateInvoice('terms_of_delivery', e.target.value)} placeholder="e.g. FOB" />
              </div>
            </div>
          </CollapsibleSection>

          {/* Product Search (preserved) */}
          <h2 className={styles.sectionTitle}>Add Products</h2>
          <div className={styles.searchContainer}>
            <input
              className={styles.searchInput}
              placeholder="Search by SKU or Name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              autoFocus
            />
            {searchResults.length > 0 && (
              <div className={styles.searchResults}>
                {searchResults.map(result => (
                  <div key={result.id} className={styles.searchItem} onClick={() => addToCart(result)}>
                    <div className={styles.searchItemMain}>
                      <span className={styles.itemName}>{result.sku} - {result.name}</span>
                      <span className={styles.itemMeta}>
                        {result.hsn_sac && `HSN: ${result.hsn_sac} | `}
                        Brand: {result.brand} | Cat: {result.category}
                      </span>
                    </div>
                    <div className={`${styles.itemStock} ${result.available_stock < 5 ? styles.low : ''}`}>
                      Stock: {result.available_stock}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Enhanced Cart Table */}
          <div className={styles.cartTableContainer}>
            <table className={styles.cartTable}>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>HSN</th>
                  <th>Qty</th>
                  <th>Unit</th>
                  <th>Rate (₹)</th>
                  <th>Disc.</th>
                  <th>GST %</th>
                  <th>Taxable</th>
                  {isInterState ? <th>IGST</th> : <><th>CGST</th><th>SGST</th></>}
                  <th>Total (₹)</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {cart.map((item, index) => (
                  <tr key={`${item.sku}-${index}`}>
                    <td>
                      <div className={styles.itemName}>{item.sku}</div>
                      <div className={styles.itemMeta}>{item.product_name || item.name}</div>
                    </td>
                    <td className={styles.hsnCell}>{item.hsn_sac || '—'}</td>
                    <td>
                      <input
                        type="number"
                        className={styles.qtyInput}
                        value={item.quantity}
                        onChange={(e) => updateCartItem(index, 'quantity', e.target.value)}
                        min="1"
                      />
                    </td>
                    <td className={styles.unitCell}>{item.unit || 'PCS'}</td>
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
                        className={styles.discInput}
                        value={item.discount}
                        onChange={(e) => updateCartItem(index, 'discount', e.target.value)}
                        step="0.01"
                        min="0"
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
                    {isInterState ? (
                      <td>₹{item.igst.toFixed(2)}</td>
                    ) : (
                      <>
                        <td>₹{item.cgst.toFixed(2)}</td>
                        <td>₹{item.sgst.toFixed(2)}</td>
                      </>
                    )}
                    <td className={styles.lineTotalCell}>₹{item.line_total.toFixed(2)}</td>
                    <td>
                      <button className={styles.removeBtn} onClick={() => removeFromCart(index)}>
                        <FiX />
                      </button>
                    </td>
                  </tr>
                ))}
                {cart.length === 0 && (
                  <tr>
                    <td colSpan={isInterState ? 11 : 12} style={{textAlign: 'center', padding: '24px', color: '#666'}}>
                      Cart is empty. Search products to add.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary Panel */}
        <div className={styles.summaryPanel}>
          <h2 className={styles.sectionTitle}>Bill Summary</h2>

          <div className={styles.inputGroup} style={{marginBottom: '16px'}}>
            <label>Payment Method</label>
            <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              <option value="Cash">Cash</option>
              <option value="UPI">UPI</option>
              <option value="Card">Card</option>
              <option value="Bank Transfer">Bank Transfer</option>
              <option value="Cheque">Cheque</option>
              <option value="Credit">Credit</option>
            </select>
          </div>

          {paymentMethod !== 'Cash' && (
            <div className={styles.inputGroup} style={{marginBottom: '16px'}}>
              <label>Transaction Reference</label>
              <input
                value={paymentReference}
                onChange={e => setPaymentReference(e.target.value)}
                placeholder={paymentMethod === 'UPI' ? 'UPI Txn ID' : paymentMethod === 'Cheque' ? 'Cheque No.' : 'Reference'}
              />
            </div>
          )}

          <div className={styles.summaryRow}>
            <span>Taxable Amount</span>
            <span>₹{totals.taxable.toFixed(2)}</span>
          </div>
          {isInterState ? (
            <div className={styles.summaryRow}>
              <span>IGST</span>
              <span>₹{totals.igst.toFixed(2)}</span>
            </div>
          ) : (
            <>
              <div className={styles.summaryRow}>
                <span>CGST</span>
                <span>₹{totals.cgst.toFixed(2)}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>SGST</span>
                <span>₹{totals.sgst.toFixed(2)}</span>
              </div>
            </>
          )}
          <div className={`${styles.summaryRow} ${styles.total}`}>
            <span>Grand Total</span>
            <span>₹{totals.grand.toFixed(2)}</span>
          </div>

          {invoiceType === 'B2B' && (
            <div className={styles.b2bNotice}>
              B2B Invoice — will attempt Tally sync if enabled
            </div>
          )}

          <button
            className={styles.checkoutBtn}
            disabled={cart.length === 0 || hasUnconfirmedGst || checkoutMutation.isPending}
            onClick={handleCheckout}
          >
            {checkoutMutation.isPending ? 'Processing…' : hasUnconfirmedGst ? "Confirm GST Rates" : `Complete Sale — ₹${totals.grand.toFixed(2)}`}
          </button>
        </div>
      </div>
      {completedReceipt && (
        <ReceiptModal 
          receipt={completedReceipt} 
          onClose={() => setCompletedReceipt(null)} 
        />
      )}
    </div>
  );
};

export default POSPage;

import React from 'react';
import styles from '../InvoiceRenderer.module.css';

const formatDate = (dateString) => {
  if (!dateString) return '';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return String(dateString);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  } catch {
    return String(dateString);
  }
};

const InvoiceDetailsBox = ({ invoice }) => {
  const customer = invoice?.customer || {};
  const shipping = invoice?.shipping;
  
  const customerName = customer?.name || '';
  const customerPhone = customer?.phone || customer?.mobile || '';
  const customerGstin = customer?.gstin || '';
  const customerAddress = customer?.address || '';
  const customerPincode = customer?.pincode || customer?.postal_code || '';

  const shippingName = shipping?.name || customerName;
  const shippingPhone = shipping?.phone || shipping?.mobile || customerPhone;
  const shippingAddress = shipping?.address || '';

  const billNo = invoice?.invoice_number || invoice?.bill_number || '';
  const billDate = formatDate(invoice?.date || invoice?.sale_date || invoice?.created_at);
  const payMode = (invoice?.payment_method || 'CREDIT').toUpperCase();
  const transportMode = invoice?.dispatch_through || invoice?.transport_mode || '';
  const orderNo = invoice?.buyer_order_no || invoice?.order_no || '';
  const lutNo = invoice?.lut_no || '';

  return (
    <div className={styles.partyBoxContainer}>
      {/* Column 1: Billed to */}
      <div className={styles.partyColBilled}>
        <div className={styles.partyBoxHeader}>Billed to :</div>
        <div className={styles.partyBoxRow}>
          <strong>M/S : </strong>{customerName}{customerPhone ? ` - ${customerPhone}` : ''}
        </div>
        {customerAddress && (
          <div className={styles.partyBoxRow}>{customerAddress}</div>
        )}
        <div className={styles.partyBoxRow}>
          <strong>PIN CODE:</strong> {customerPincode}
        </div>
        <div className={styles.partyBoxRow}>
          <strong>GST NO:- </strong>{customerGstin}
        </div>
        <div className={styles.partyBoxRow}>
          <strong>PHONE NO.: </strong>{customerPhone}
        </div>
      </div>

      {/* Column 2: Bill Info & Transport */}
      <div className={styles.partyColMeta}>
        <div className={styles.metaRowLine}>
          <span className={styles.metaKey}>BILL NO.</span>
          <span className={styles.metaSep}>:</span>
          <span className={styles.metaValBold}>{billNo}</span>
        </div>
        <div className={styles.metaRowLine}>
          <span className={styles.metaKey}>DATE</span>
          <span className={styles.metaSep}>:</span>
          <span className={styles.metaVal}>{billDate}</span>
        </div>
        <div className={styles.metaRowLine}>
          <span className={styles.metaKey}>PAY MODE</span>
          <span className={styles.metaSep}>:</span>
          <span className={styles.metaVal}>{payMode}</span>
        </div>
        {orderNo && (
          <div className={styles.metaRowLine}>
            <span className={styles.metaKey}>ORDER No.</span>
            <span className={styles.metaSep}>:</span>
            <span className={styles.metaVal}>{orderNo}</span>
          </div>
        )}
        <div className={styles.metaRowLine}>
          <span className={styles.metaKey}>TRANSPORT MODE</span>
          <span className={styles.metaSep}>:-</span>
          <span className={styles.metaVal}>{transportMode}</span>
        </div>
        <div className={styles.metaRowLine}>
          <span className={styles.metaKey}>LUT NO</span>
          <span className={styles.metaSep}>:</span>
          <span className={styles.metaVal}>{lutNo}</span>
        </div>
      </div>

      {/* Column 3: Shipped to */}
      <div className={styles.partyColShipped}>
        <div className={styles.partyBoxHeader}>Shipped to :</div>
        <div className={styles.partyBoxRow}>
          {shippingName}{shippingPhone ? ` - ${shippingPhone}` : ''}
        </div>
        {shippingAddress && (
          <div className={styles.partyBoxRow}>{shippingAddress}</div>
        )}
        <div className={styles.partyBoxRowOrder}>
          <strong>ORDER No.: </strong>{orderNo}
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetailsBox;

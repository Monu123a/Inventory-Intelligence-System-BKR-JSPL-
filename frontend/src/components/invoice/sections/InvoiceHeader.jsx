import React from 'react';
import styles from '../InvoiceRenderer.module.css';

const InvoiceHeader = ({ company, invoiceType, tallyData }) => {
  // If we have actual IRN and QR data in tallyData, we could display it here.
  // For now, we only show it if tallyData has e_invoice_details (which we will add in future)
  const hasEInvoice = tallyData && tallyData.irn;

  return (
    <div className={styles.header}>
      <div className={styles.logoContainer}>
        <img 
          src={company?.logo_url || "/logo.png"} 
          alt="Company Logo" 
          className={styles.companyLogo} 
          onError={(e) => {
            e.target.style.display = 'none';
            if (e.target.nextSibling) e.target.nextSibling.style.display = 'block';
          }} 
        />
        <h1 className={styles.partyName} style={{ display: (company?.logo_url || '/logo.png') ? 'none' : 'block' }}>{company?.name}</h1>
      </div>
      
      <div className={styles.titleBox}>
        <h2 className={styles.invoiceTitle}>TAX INVOICE</h2>
        <div className={styles.invoiceType}>{invoiceType}</div>
      </div>
      
      <div className={styles.eInvoiceSection}>
        {hasEInvoice ? (
          <div className={styles.eInvoiceDetails}>
            {/* Real QR and IRN would go here */}
            <div>IRN: {tallyData.irn}</div>
            <div>Ack No: {tallyData.ack_no}</div>
            <div>Ack Date: {tallyData.ack_date}</div>
          </div>
        ) : (
          <div className={styles.eInvoicePlaceholder}></div>
        )}
      </div>
    </div>
  );
};

export default InvoiceHeader;

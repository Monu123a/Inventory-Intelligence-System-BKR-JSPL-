import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import styles from '../InvoiceRenderer.module.css';

const InvoiceHeader = ({ company, invoiceType, tallyData, items, einvoice }) => {
  const hasOnlyZeroGst = items?.length > 0 && items.every(item => parseFloat(item.gst_rate || 0) === 0);
  const invoiceTitle = hasOnlyZeroGst ? 'BILL OF SUPPLY' : 'TAX INVOICE';
  
  const irn = einvoice?.irn || tallyData?.irn;
  const ackNo = einvoice?.ack_no || tallyData?.ack_no;
  const ackDate = einvoice?.ack_date || tallyData?.ack_date;
  const qrCodeData = einvoice?.qr_code_data || tallyData?.qr_code_data || irn;
  const hasEInvoice = Boolean(irn && einvoice?.status !== 'CANCELLED');

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
        <h2 className={styles.invoiceTitle}>{invoiceTitle}</h2>
      </div>
      
      <div className={styles.eInvoiceSection}>
        {hasEInvoice ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
            <div style={{ textAlign: 'right', fontSize: '9px', lineHeight: '1.3', color: '#1e293b' }}>
              <div style={{ fontWeight: 700, color: '#1d4ed8' }}>e-Invoice Verified</div>
              <div style={{ wordBreak: 'break-all', maxWidth: '170px', fontFamily: 'monospace', fontSize: '8px' }}>
                <strong>IRN:</strong> {irn.length > 28 ? `${irn.substring(0, 16)}...${irn.substring(irn.length - 8)}` : irn}
              </div>
              <div><strong>Ack No:</strong> {ackNo}</div>
              {ackDate && <div><strong>Ack Dt:</strong> {new Date(ackDate).toLocaleDateString('en-IN')}</div>}
            </div>
            {qrCodeData && (
              <div style={{ padding: '2px', background: '#fff', border: '1px solid #cbd5e1', borderRadius: '4px', display: 'flex' }}>
                <QRCodeSVG value={qrCodeData} size={64} level="M" />
              </div>
            )}
          </div>
        ) : (
          <div className={styles.eInvoicePlaceholder}></div>
        )}
      </div>
    </div>
  );
};

export default InvoiceHeader;

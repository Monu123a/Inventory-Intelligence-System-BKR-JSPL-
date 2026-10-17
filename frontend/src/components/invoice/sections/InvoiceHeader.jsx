import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import styles from '../InvoiceRenderer.module.css';

const InvoiceHeader = ({ company, invoiceType, tallyData, items, einvoice }) => {
  const hasOnlyZeroGst = items?.length > 0 && items.every(item => parseFloat(item.gst_rate || 0) === 0);
  const invoiceTitle = hasOnlyZeroGst ? 'BILL OF SUPPLY' : 'TAX INVOICE';
  
  const rawIrn = einvoice?.irn || tallyData?.irn;
  const irn = rawIrn ? String(rawIrn) : '';
  const ackNo = einvoice?.ack_no || tallyData?.ack_no;
  const ackDate = einvoice?.ack_date || tallyData?.ack_date;
  const rawQr = einvoice?.qr_code_data || tallyData?.qr_code_data || irn;
  const qrCodeData = typeof rawQr === 'string' ? rawQr : (rawQr ? JSON.stringify(rawQr) : '');
  const hasEInvoice = Boolean(irn && einvoice?.status !== 'CANCELLED');

  const formattedAckDate = React.useMemo(() => {
    if (!ackDate) return '';
    try {
      const d = new Date(ackDate);
      return isNaN(d.getTime()) ? String(ackDate) : d.toLocaleDateString('en-IN');
    } catch {
      return String(ackDate);
    }
  }, [ackDate]);

  const coNameUpper = (company?.name || company?.legal_name || '').toUpperCase();
  const coCodeUpper = (company?.code || '').toUpperCase();
  const isJspl = !coCodeUpper || coCodeUpper === 'JSPL' || coNameUpper.includes('SHOPSMART') || coNameUpper.includes('HALTE') || (coNameUpper.includes('JAGAN') && !coNameUpper.includes('RAMAN'));

  const gstNo = company?.gstin || (isJspl ? '04AAFCJ8215N1ZC' : '');
  const brandName = isJspl ? 'HALTE' : (company?.trade_name || company?.name || '');
  const legalName = isJspl ? 'C/O Jagan Shopsmart Pvt Ltd.' : (company?.name || '');
  const addressLine1 = isJspl ? 'Plot No. 150,Business & Industrial Park-2,' : (company?.address || '');
  const addressLine2 = isJspl ? 'Chandigarh, India - 160002,,Godown/Workshop: 24/9, Industrial Park-2' : `${company?.state || ''} ${company?.state_code ? `(${company.state_code})` : ''}`;
  const email = company?.email || (isJspl ? 'halteindia@gmail.com' : '');
  const website = company?.website || (isJspl ? 'www.halte.in' : '');
  const phones = isJspl 
    ? ['9914130130,9216407929,', '9872607929,9501200185'] 
    : (company?.phone ? [company.phone] : []);
  const logoSrc = isJspl ? '/halte_logo.png' : (company?.logo_url || '/logo.png');

  return (
    <div className={styles.headerContainer}>
      {/* Top Left: GST No & QRs */}
      <div className={styles.headerLeft}>
        <div className={styles.gstinLabel}>
          <strong>GST NO. :</strong>{gstNo}
        </div>
        <div className={styles.qrRow}>
          {hasEInvoice && (
            <div className={styles.eInvoiceBlock}>
              {qrCodeData && (
                <div className={styles.qrCodeWrapper}>
                  <QRCodeSVG value={qrCodeData} size={64} level="M" />
                </div>
              )}
              <div className={styles.eInvoiceMeta}>
                <div style={{ fontWeight: 700, color: '#1d4ed8' }}>e-Invoice</div>
                <div>IRN: {irn.length > 16 ? `${irn.substring(0, 8)}...${irn.substring(irn.length - 6)}` : irn}</div>
                {ackNo && <div>Ack: {ackNo}</div>}
                {formattedAckDate && <div>Dt: {formattedAckDate}</div>}
              </div>
            </div>
          )}
          {isJspl && (
            <div className={styles.instaQrBlock}>
              <img src="/halte_insta_qr.png" alt="@HALTE.INDIA" className={styles.instaQrImg} />
            </div>
          )}
        </div>
      </div>

      {/* Center: Title & Company details */}
      <div className={styles.headerCenter}>
        <div className={styles.taxInvoiceTitle}>{invoiceTitle}</div>
        <div className={styles.mainBrandName}>{brandName}</div>
        {legalName && <div className={styles.coLegalName}>{legalName}</div>}
        {addressLine1 && <div className={styles.headerAddress}>{addressLine1}</div>}
        {addressLine2 && <div className={styles.headerAddress}>{addressLine2}</div>}
        <div className={styles.headerContactLine}>
          {email && <span><strong>EMAIL :- </strong>{email}</span>}
          {website && <span className={styles.shopOnlineCenter}><strong>Shop Online - </strong>{website}</span>}
        </div>
      </div>

      {/* Top Right: Phones, Logo, Shop Online */}
      <div className={styles.headerRight}>
        <div className={styles.phoneBlock}>
          {phones.length > 0 && <span><strong>PH NO.</strong>{phones[0]}</span>}
          {phones.length > 1 && <div>{phones[1]}</div>}
        </div>
        <div className={styles.headerLogoWrapper}>
          <img 
            src={logoSrc} 
            alt="Logo" 
            className={styles.headerLogoImg}
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        </div>
        {website && (
          <div className={styles.headerShopOnline}>
            <strong>Shop Online - </strong>{website}
          </div>
        )}
      </div>
    </div>
  );
};

export default InvoiceHeader;

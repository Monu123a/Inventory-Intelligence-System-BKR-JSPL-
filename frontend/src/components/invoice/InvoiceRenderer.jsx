import React, { forwardRef } from 'react';
import styles from './InvoiceRenderer.module.css';
import InvoiceHeader from './sections/InvoiceHeader';
import InvoiceDetailsBox from './sections/InvoiceDetailsBox';
import InvoiceItems from './sections/InvoiceItems';
import InvoiceSummary from './sections/InvoiceSummary';

const InvoiceRenderer = forwardRef(({ invoice }, ref) => {
  if (!invoice) return null;

  const sellerStateCode = invoice.company?.state_code || (invoice.company?.gstin ? invoice.company.gstin.substring(0, 2) : '04');
  const buyerStateCode = invoice.customer?.state_code || (invoice.customer?.gstin ? invoice.customer.gstin.substring(0, 2) : '');
  const itemsHaveIGST = invoice.items?.some(item => parseFloat(item.igst || 0) > 0);
  const isInterState = itemsHaveIGST || Boolean(buyerStateCode && buyerStateCode !== sellerStateCode);

  return (
    <div className={styles.invoiceWrapper} ref={ref} style={{ position: 'relative' }}>
      {invoice.status === 'Cancelled' && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%) rotate(-45deg)',
          fontSize: '100px', color: 'rgba(239, 68, 68, 0.15)', fontWeight: 'bold', pointerEvents: 'none',
          whiteSpace: 'nowrap', zIndex: 10, letterSpacing: '10px'
        }}>
          CANCELLED
        </div>
      )}
      <div className={styles.invoiceContent}>
        <InvoiceHeader 
          company={invoice.company} 
          invoiceType={invoice.invoice_type} 
          tallyData={invoice.tally} 
          items={invoice.items}
          einvoice={invoice.einvoice || {
            irn: invoice.einvoice_irn,
            ack_no: invoice.einvoice_ack_no,
            ack_date: invoice.einvoice_ack_date,
            qr_code_data: invoice.einvoice_qr_code_data,
            status: invoice.einvoice_status,
            eway_bill_number: invoice.eway_bill_number
          }}
        />

        <InvoiceDetailsBox invoice={invoice} />

        <InvoiceItems 
          items={invoice.items} 
          totals={invoice.totals} 
          isInterState={isInterState}
        />

        <InvoiceSummary 
          company={invoice.company} 
          customer={invoice.customer}
          items={invoice.items} 
          totals={invoice.totals} 
        />
      </div>
    </div>
  );
});

InvoiceRenderer.displayName = 'InvoiceRenderer';

export default InvoiceRenderer;

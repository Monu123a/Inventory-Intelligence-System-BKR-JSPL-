import React, { forwardRef } from 'react';
import styles from './InvoiceRenderer.module.css';
import InvoiceHeader from './sections/InvoiceHeader';
import InvoiceParties from './sections/InvoiceParties';
import InvoiceMeta from './sections/InvoiceMeta';
import InvoiceItems from './sections/InvoiceItems';
import InvoiceSummary from './sections/InvoiceSummary';

const InvoiceRenderer = forwardRef(({ invoice }, ref) => {
  if (!invoice) return null;

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
        />
        
        <div className={styles.middleSection}>
          <div className={styles.leftColumn}>
            <InvoiceParties 
              company={invoice.company} 
              customer={invoice.customer} 
              shipping={invoice.shipping}
            />
          </div>
          <div className={styles.rightColumn}>
            <InvoiceMeta invoice={invoice} />
          </div>
        </div>

        <InvoiceItems 
          items={invoice.items} 
          totals={invoice.totals} 
        />

        <InvoiceSummary 
          company={invoice.company} 
          items={invoice.items} 
          totals={invoice.totals} 
        />
      </div>
    </div>
  );
});

InvoiceRenderer.displayName = 'InvoiceRenderer';

export default InvoiceRenderer;

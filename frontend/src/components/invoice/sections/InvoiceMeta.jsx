import React from 'react';
import styles from '../InvoiceRenderer.module.css';

const InvoiceMeta = ({ invoice }) => {
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  return (
    <div className={styles.metaContainer}>
      <div className={styles.metaGrid}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Invoice No.</span>
          <span className={styles.metaValue}>{invoice.invoice_number}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Invoice Date</span>
          <span className={styles.metaValue}>{formatDate(invoice.sale_date)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Payment Terms</span>
          <span className={styles.metaValue}>{invoice.payment_terms || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Delivery Note</span>
          <span className={styles.metaValue}>{invoice.delivery_note || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Delivery Note Date</span>
          <span className={styles.metaValue}>{formatDate(invoice.delivery_note_date) || '-'}</span>
        </div>
      </div>

      <div className={styles.metaGrid}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Dispatch Doc No.</span>
          <span className={styles.metaValue}>{invoice.dispatch_document_number || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Dispatch Through</span>
          <span className={styles.metaValue}>{invoice.dispatch_through || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Destination</span>
          <span className={styles.metaValue}>{invoice.destination || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Vehicle No.</span>
          <span className={styles.metaValue}>{invoice.vehicle_number || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>LR/RR No.</span>
          <span className={styles.metaValue}>{invoice.lr_rr_number || '-'}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Terms of Delivery</span>
          <span className={styles.metaValue}>{invoice.terms_of_delivery || '-'}</span>
        </div>
      </div>
    </div>
  );
};

export default InvoiceMeta;

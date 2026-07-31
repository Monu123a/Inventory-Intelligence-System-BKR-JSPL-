import React from 'react';
import styles from '../InvoiceRenderer.module.css';

const InvoiceParties = ({ company, customer }) => {
  return (
    <div className={styles.partiesGrid}>
      <div className={styles.partyBox}>
        <div className={styles.partyLabel}>Seller / Billed By</div>
        <div className={styles.partyName}>{company?.name}</div>
        <div className={styles.partyDetail}>{company?.address}</div>
        <div className={styles.partyDetail}>{company?.state} {company?.state_code ? `(Code: ${company.state_code})` : ''}</div>
        <div className={styles.partyDetail}><strong>GSTIN:</strong> {company?.gstin}</div>
        {company?.email && <div className={styles.partyDetail}><strong>Email:</strong> {company.email}</div>}
        {company?.phone && <div className={styles.partyDetail}><strong>Phone:</strong> {company.phone}</div>}
      </div>
      
      <div className={styles.partyBox}>
        <div className={styles.partyLabel}>Buyer / Billed To</div>
        <div className={styles.partyName}>{customer?.name}</div>
        <div className={styles.partyDetail}>{customer?.address}</div>
        <div className={styles.partyDetail}>{customer?.state} {customer?.state_code ? `(Code: ${customer.state_code})` : ''}</div>
        <div className={styles.partyDetail}><strong>GSTIN:</strong> {customer?.gstin}</div>
        {customer?.place_of_supply && <div className={styles.partyDetail}><strong>Place of Supply:</strong> {customer.place_of_supply}</div>}
      </div>
    </div>
  );
};

export default InvoiceParties;

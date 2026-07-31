import React from 'react';
import styles from '../InvoiceRenderer.module.css';

const formatCurrency = (val) => {
  return Number(val || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

const InvoiceItems = ({ items, totals }) => {
  return (
    <table className={styles.itemsTable}>
      <thead>
        <tr>
          <th className={styles.textCenter}>Sl No.</th>
          <th className={styles.textLeft}>Description of Goods</th>
          <th className={styles.textCenter}>HSN/SAC</th>
          <th className={styles.textCenter}>GST Rate</th>
          <th className={styles.textCenter}>Quantity</th>
          <th className={styles.textCenter}>per</th>
          <th className={styles.textRight}>Rate</th>
          <th className={styles.textRight}>Disc.</th>
          <th className={styles.textRight}>Amount</th>
        </tr>
      </thead>
      <tbody>
        {items?.map((item, index) => (
          <tr key={index}>
            <td className={styles.textCenter}>{index + 1}</td>
            <td className={styles.textLeft}>{item.product_name} {item.sku && <small><br/>SKU: {item.sku}</small>}</td>
            <td className={styles.textCenter}>{item.hsn_sac}</td>
            <td className={styles.textCenter}>{item.gst_rate}%</td>
            <td className={styles.textCenter}>{item.quantity}</td>
            <td className={styles.textCenter}>{item.unit}</td>
            <td className={styles.textRight}>{formatCurrency(item.rate)}</td>
            <td className={styles.textRight}>{formatCurrency(item.discount)}</td>
            <td className={styles.textRight}>{formatCurrency(item.taxable_value)}</td>
          </tr>
        ))}
        
        <tr className={styles.totalsRow}>
          <td colSpan="4" className={styles.textRight}>Total</td>
          <td className={styles.textCenter}>
            {items?.reduce((sum, item) => sum + parseFloat(item.quantity || 0), 0)}
          </td>
          <td colSpan="3" className={styles.textRight}>Taxable Amount</td>
          <td className={styles.textRight}>{formatCurrency(totals?.taxable_amount)}</td>
        </tr>
      </tbody>
    </table>
  );
};

export default InvoiceItems;

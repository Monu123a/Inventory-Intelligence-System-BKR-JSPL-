import React from 'react';
import styles from '../InvoiceRenderer.module.css';
import { amountInWords } from '../../../utils/amountInWords';

const formatCurrency = (val) => {
  return Number(val || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

const InvoiceSummary = ({ company, items, totals }) => {
  const hasIGST = items?.some(item => parseFloat(item.igst || 0) > 0);

  const gstSummary = items?.reduce((acc, item) => {
    const rate = item.gst_rate || 0;
    if (!acc[rate]) {
      acc[rate] = { taxable_value: 0, cgst: 0, sgst: 0, igst: 0, total_tax: 0, hsn: item.hsn_sac };
    }
    acc[rate].taxable_value += parseFloat(item.taxable_value || 0);
    acc[rate].cgst += parseFloat(item.cgst || 0);
    acc[rate].sgst += parseFloat(item.sgst || 0);
    acc[rate].igst += parseFloat(item.igst || 0);
    acc[rate].total_tax += parseFloat(item.cgst || 0) + parseFloat(item.sgst || 0) + parseFloat(item.igst || 0);
    return acc;
  }, {});

  const gstSummaryEntries = Object.entries(gstSummary || {}).sort((a, b) => Number(a[0]) - Number(b[0]));

  const totalTaxAmount = gstSummaryEntries.reduce((sum, [_, vals]) => sum + vals.total_tax, 0);

  return (
    <div className={styles.summaryContainer}>
      <div className={styles.amountChargeable}>
        Amount Chargeable (in words)<br/>
        <strong>INR {totals?.grand_total ? amountInWords(totals.grand_total) : ''}</strong>
      </div>

      {gstSummaryEntries.length > 0 && (
        <table className={styles.gstSummaryTable}>
          <thead>
            <tr>
              <th rowSpan="2" className={styles.textCenter}>HSN/SAC</th>
              <th rowSpan="2" className={styles.textRight}>Taxable Value</th>
              {hasIGST ? (
                <th colSpan="2" className={styles.textCenter}>IGST</th>
              ) : (
                <>
                  <th colSpan="2" className={styles.textCenter}>CGST</th>
                  <th colSpan="2" className={styles.textCenter}>SGST/UTGST</th>
                </>
              )}
              <th rowSpan="2" className={styles.textRight}>Total Tax Amount</th>
            </tr>
            <tr>
              {hasIGST ? (
                <>
                  <th className={styles.textCenter}>Rate</th>
                  <th className={styles.textRight}>Amount</th>
                </>
              ) : (
                <>
                  <th className={styles.textCenter}>Rate</th>
                  <th className={styles.textRight}>Amount</th>
                  <th className={styles.textCenter}>Rate</th>
                  <th className={styles.textRight}>Amount</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {gstSummaryEntries.map(([rate, vals], idx) => (
              <tr key={idx}>
                <td className={styles.textCenter}>{vals.hsn}</td>
                <td className={styles.textRight}>{formatCurrency(vals.taxable_value)}</td>
                {hasIGST ? (
                  <>
                    <td className={styles.textCenter}>{rate}%</td>
                    <td className={styles.textRight}>{formatCurrency(vals.igst)}</td>
                  </>
                ) : (
                  <>
                    <td className={styles.textCenter}>{Number(rate)/2}%</td>
                    <td className={styles.textRight}>{formatCurrency(vals.cgst)}</td>
                    <td className={styles.textCenter}>{Number(rate)/2}%</td>
                    <td className={styles.textRight}>{formatCurrency(vals.sgst)}</td>
                  </>
                )}
                <td className={styles.textRight}>{formatCurrency(vals.total_tax)}</td>
              </tr>
            ))}
            <tr className={styles.totalsRow}>
              <td className={styles.textRight}>Total</td>
              <td className={styles.textRight}>{formatCurrency(totals?.taxable_amount)}</td>
              {hasIGST ? (
                <>
                  <td></td>
                  <td className={styles.textRight}>{formatCurrency(items?.reduce((sum, item) => sum + parseFloat(item.igst || 0), 0))}</td>
                </>
              ) : (
                <>
                  <td></td>
                  <td className={styles.textRight}>{formatCurrency(items?.reduce((sum, item) => sum + parseFloat(item.cgst || 0), 0))}</td>
                  <td></td>
                  <td className={styles.textRight}>{formatCurrency(items?.reduce((sum, item) => sum + parseFloat(item.sgst || 0), 0))}</td>
                </>
              )}
              <td className={styles.textRight}>{formatCurrency(totalTaxAmount)}</td>
            </tr>
          </tbody>
        </table>
      )}

      <div className={styles.taxAmountWords}>
        Tax Amount (in words) : <strong>INR {amountInWords(totalTaxAmount)}</strong>
      </div>

      <div className={styles.footerLayout}>
        <div className={styles.footerLeft}>
          {company?.bank_details && (
            <div className={styles.bankSection}>
              <div className={styles.bankTitle}>Bank Details</div>
              <div><strong>Bank Name:</strong> {company.bank_details.bank_name}</div>
              <div><strong>Account No:</strong> {company.bank_details.account_no}</div>
              <div><strong>IFSC Code:</strong> {company.bank_details.ifsc}</div>
              <div><strong>Branch:</strong> {company.bank_details.branch}</div>
              {company.bank_details.upi && <div><strong>UPI:</strong> {company.bank_details.upi}</div>}
            </div>
          )}
          <div className={styles.declarationSection}>
            <div className={styles.declarationTitle}>Declaration</div>
            <div>We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.</div>
          </div>
        </div>
        
        <div className={styles.footerRight}>
          <div className={styles.signCompany}>for {company?.name}</div>
          <div className={styles.signSpace}></div>
          <div className={styles.signLabel}>Authorised Signatory</div>
        </div>
      </div>
      
      <div className={styles.footerDisclaimer}>
        <div>SUBJECT TO {company?.state?.toUpperCase()} JURISDICTION</div>
        <div>This is a Computer Generated Invoice</div>
      </div>
    </div>
  );
};

export default InvoiceSummary;

import React from 'react';
import styles from '../InvoiceRenderer.module.css';
import { amountInWords } from '../../../utils/amountInWords';

const formatCurrency = (val) => {
  return Number(val || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

const InvoiceSummary = ({ company, customer, items = [], totals }) => {
  // Determine state codes
  const sellerStateCode = company?.state_code || (company?.gstin ? company.gstin.substring(0, 2) : '04');
  const buyerStateCode = customer?.state_code || (customer?.gstin ? customer.gstin.substring(0, 2) : '');
  
  // Check if items have IGST or place of supply is interstate
  const itemsHaveIGST = items.some(item => parseFloat(item.igst || 0) > 0);
  const isInterState = itemsHaveIGST || Boolean(buyerStateCode && buyerStateCode !== sellerStateCode);
  const isUT = ['04', '35', '38', '31', '26'].includes(sellerStateCode) || (company?.state && company.state.toUpperCase().includes('CHANDIGARH'));

  // Calculate totals from items
  const totalSoldQty = items.reduce((sum, item) => sum + parseFloat(item.remaining_quantity ?? item.quantity ?? 0), 0);
  const totalTaxable = totals?.taxable_amount ?? items.reduce((sum, item) => sum + parseFloat(item.taxable_value || item.taxable_amount || 0), 0);
  
  const totalCGST = items.reduce((sum, item) => sum + parseFloat(item.cgst || 0), 0);
  const totalSGST = items.reduce((sum, item) => sum + parseFloat(item.sgst || 0), 0);
  const totalIGST = items.reduce((sum, item) => sum + parseFloat(item.igst || 0), 0);
  
  const rawTotalTax = isInterState ? totalIGST : (totalCGST + totalSGST);
  const rawGrandTotal = totalTaxable + rawTotalTax;
  const roundedGrandTotal = totals?.grand_total ? Math.round(totals.grand_total) : Math.round(rawGrandTotal);
  const roundOff = parseFloat((roundedGrandTotal - rawGrandTotal).toFixed(2));

  // Compute GST Slabs: 0 (Taxfree), 5, 12, 18, 28
  const slabs = {
    0: { taxable: 0, sgst_utgst: 0, cgst: 0, igst: 0 },
    5: { taxable: 0, sgst_utgst: 0, cgst: 0, igst: 0 },
    12: { taxable: 0, sgst_utgst: 0, cgst: 0, igst: 0 },
    18: { taxable: 0, sgst_utgst: 0, cgst: 0, igst: 0 },
    28: { taxable: 0, sgst_utgst: 0, cgst: 0, igst: 0 },
  };

  items.forEach(item => {
    const rate = Math.round(parseFloat(item.gst_rate || 0));
    const taxable = parseFloat(item.taxable_value || item.taxable_amount || 0);
    const itemCgst = parseFloat(item.cgst || 0);
    const itemSgst = parseFloat(item.sgst || 0);
    const itemIgst = parseFloat(item.igst || 0);

    const targetKey = slabs[rate] !== undefined ? rate : 18;
    slabs[targetKey].taxable += taxable;
    slabs[targetKey].cgst += itemCgst;
    slabs[targetKey].sgst_utgst += itemSgst;
    slabs[targetKey].igst += itemIgst;
  });

  const coNameUpper = (company?.name || company?.legal_name || '').toUpperCase();
  const coCodeUpper = (company?.code || '').toUpperCase();
  const isJspl = coCodeUpper === 'JSPL' || coNameUpper.includes('SHOPSMART') || (coNameUpper.includes('JAGAN') && !coNameUpper.includes('RAMAN'));
  const bankDetails = company?.bank_details || {};
  
  const bankInfo = {
    name: isJspl ? 'JAGAN SHOPSMART PVT LTD' : (bankDetails.account_name || 'B.K. RAMAN & CO (CA)'),
    accountNumber: (bankDetails.account_no || bankDetails.account_number || (isJspl ? '50200075992904' : '41836801381')).trim(),
    branch: (bankDetails.branch || (isJspl ? 'CHD- INDUSTRIAL AREA PH-II' : 'Industrial Area, Phase-2')).trim(),
    accountType: (bankDetails.account_type || 'CURRENT ACCOUNT').trim(),
    ifsc: (bankDetails.ifsc || (isJspl ? 'HDFC0001417' : 'SBIN0007501')).trim(),
    bankName: (bankDetails.bank_name || (isJspl ? 'HDFC Bank Ltd' : 'State Bank Of India')).trim(),
    city: (bankDetails.city || 'Chandigarh').trim()
  };

  const sgstUtgstLabel = isUT ? 'ADD UTGST' : 'ADD SGST';
  const gridSgstUtgstCol = isUT ? 'UTGST' : 'GST';

  return (
    <div className={styles.summaryContainerModern}>
      {/* Upper totals section matching Image 2 */}
      <table className={styles.upperTotalsTable}>
        <tbody>
          <tr>
            <td className={styles.emptyLeftCell}></td>
            <td className={styles.totalsLabelCell}>TOTAL</td>
            <td className={styles.totalsQtyCell}>{totalSoldQty}</td>
            <td className={styles.totalsValueCell}>{formatCurrency(totalTaxable)}</td>
          </tr>
          {isInterState ? (
            <tr>
              <td className={styles.emptyLeftCell}></td>
              <td colSpan="2" className={styles.totalsLabelCell}>ADD IGST</td>
              <td className={styles.totalsValueCell}>{formatCurrency(totalIGST)}</td>
            </tr>
          ) : (
            <>
              <tr>
                <td className={styles.emptyLeftCell}></td>
                <td colSpan="2" className={styles.totalsLabelCell}>{sgstUtgstLabel}</td>
                <td className={styles.totalsValueCell}>{formatCurrency(totalSGST)}</td>
              </tr>
              <tr>
                <td className={styles.emptyLeftCell}></td>
                <td colSpan="2" className={styles.totalsLabelCell}>ADD CGST</td>
                <td className={styles.totalsValueCell}>{formatCurrency(totalCGST)}</td>
              </tr>
            </>
          )}
          <tr>
            <td className={styles.wordsCell}>
              <strong>Rs.: </strong>{amountInWords(roundedGrandTotal)} Only
            </td>
            <td colSpan="2" className={styles.totalsLabelCell}>Round Off</td>
            <td className={styles.totalsValueCell}>{roundOff >= 0 ? formatCurrency(roundOff) : formatCurrency(roundOff)}</td>
          </tr>
          <tr className={styles.netAmountRow}>
            <td className={styles.emptyLeftCell}></td>
            <td colSpan="2" className={styles.netAmountLabel}>Net Amount</td>
            <td className={styles.netAmountValue}>{formatCurrency(roundedGrandTotal)}</td>
          </tr>
        </tbody>
      </table>

      {/* Double Divider Line matching Image 2 */}
      <div className={styles.doubleDivider}></div>

      {/* Lower section with GST Matrix on left and Bank Details on right */}
      <div className={styles.lowerSectionGrid}>
        <div className={styles.lowerLeftBlock}>
          <table className={styles.gstMatrixTable}>
            <tbody>
              <tr>
                <td className={styles.gstMatrixLabel}>GST SALE TAXFREE :</td>
                <td className={styles.gstMatrixTaxable}>{slabs[0].taxable > 0 ? formatCurrency(slabs[0].taxable) : ''}</td>
                <td colSpan="6"></td>
              </tr>
              {[5, 12, 18, 28].map(rate => {
                const slab = slabs[rate];
                const halfRate = rate / 2;
                return (
                  <tr key={rate}>
                    <td className={styles.gstMatrixLabel}>GST SALE {rate}% :</td>
                    <td className={styles.gstMatrixTaxable}>{slab.taxable > 0 ? formatCurrency(slab.taxable) : ''}</td>
                    <td className={styles.gstMatrixTag}>{gridSgstUtgstCol} {halfRate}%:</td>
                    <td className={styles.gstMatrixVal}>{!isInterState && slab.sgst_utgst > 0 ? formatCurrency(slab.sgst_utgst) : ''}</td>
                    <td className={styles.gstMatrixTag}>CGST {halfRate}%:</td>
                    <td className={styles.gstMatrixVal}>{!isInterState && slab.cgst > 0 ? formatCurrency(slab.cgst) : ''}</td>
                    <td className={styles.gstMatrixTag}>IGST {rate}%:</td>
                    <td className={styles.gstMatrixVal}>{isInterState && slab.igst > 0 ? formatCurrency(slab.igst) : ''}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className={styles.termsAndConditions}>
            <div className={styles.termsTitle}>Terms & Conditions:-</div>
            <div>1. GOODS ONCE SOLD WILL NOT BE TAKEN BACK.</div>
          </div>
        </div>

        <div className={styles.lowerRightBlock}>
          {isJspl ? (
            <>
              <div className={styles.bankDetailBox}>
                <div className={styles.bankDetailTitle}>OUR BANK DETAIL</div>
                <div className={styles.bankDetailRow}><strong>Bank Details-</strong>{bankInfo.name}</div>
                <div className={styles.bankDetailRow}><strong>Account Number:</strong> {bankInfo.accountNumber}</div>
                <div className={styles.bankDetailRow}><strong>Branch:</strong> {bankInfo.branch}</div>
                <div className={styles.bankDetailRow}><strong>Account Type:</strong> {bankInfo.accountType}</div>
                <div className={styles.bankDetailRow}><strong>IFSC CODE :</strong> {bankInfo.ifsc}</div>
              </div>
              <div className={styles.signatureBox}>
                <div className={styles.forCompanyTitle}>For {bankInfo.name}</div>
                <div className={styles.signSpacer}></div>
                <div className={styles.signLabel}>Authorised Signatory</div>
              </div>
            </>
          ) : (
            <>
              <div className={styles.bankDetailBox}>
                <div style={{ fontWeight: 700, fontSize: '10.5px', marginBottom: '2px' }}>
                  {bankInfo.name}
                </div>
                <div className={styles.bankDetailRow}>A/c No- {bankInfo.accountNumber}</div>
                <div className={styles.bankDetailRow}>Ifsc - {bankInfo.ifsc}</div>
                <div className={styles.bankDetailRow}>Bank - {bankInfo.bankName}</div>
                <div className={styles.bankDetailRow}>{bankInfo.branch}</div>
                <div className={styles.bankDetailRow}>{bankInfo.city}</div>
              </div>
              <div className={styles.signatureBox}>
                <div className={styles.signSpacer}></div>
                <div className={styles.signLabel}>AUTH. SIGNATURY.</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default InvoiceSummary;

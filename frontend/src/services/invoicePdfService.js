/**
 * Simple service to download invoice as PDF using browser's print-to-pdf functionality.
 * This acts as a bridge until backend PDF generation is implemented.
 */
export function downloadInvoicePdf(invoiceRef, invoiceNumber) {
  // Note: This uses window.print() approach which works, but is limited compared to server-side PDF generation.
  if (!invoiceRef) return;

  const htmlContent = invoiceRef.outerHTML || invoiceRef.innerHTML;
  
  // Try to gather styles from the current document
  let styleTags = '';
  try {
    const styles = document.querySelectorAll('style, link[rel="stylesheet"]');
    styles.forEach(style => {
      styleTags += style.outerHTML;
    });
  } catch (e) {
    console.warn('Could not copy styles for PDF generation', e);
  }

  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow pop-ups to download PDF');
    return;
  }

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Invoice_${invoiceNumber || 'Download'}</title>
        ${styleTags}
        <style>
          @page { size: auto; margin: 10mm; }
          body { 
            margin: 0; 
            padding: 20px; 
            background: white; 
            font-family: 'Inter', sans-serif;
          }
          /* Ensure we print what we see */
          @media print {
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          }
        </style>
      </head>
      <body>
        ${htmlContent}
        <script>
          // Wait for images and styles to load before printing
          window.onload = () => {
            setTimeout(() => {
              window.print();
              setTimeout(() => window.close(), 500); // Close window after print dialog
            }, 500);
          };
        </script>
      </body>
    </html>
  `);
  
  printWindow.document.close();
}

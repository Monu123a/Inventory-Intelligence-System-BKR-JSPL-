import re

with open("frontend/src/pages/POS/InvoicePreviewPage.jsx", "r") as f:
    content = f.read()

old_buttons = """          <button className={styles.actionButton} onClick={handlePrint}>
            <FiPrinter /> Print
          </button>"""
new_buttons = """          {invoice.status !== 'Cancelled' && (!invoice.related_returns || invoice.related_returns.length === 0) && (
            <button className={styles.actionButton} onClick={() => navigate(`/sales/${invoice.id}/edit`)}>
              <FiEdit style={{ marginRight: '4px' }} /> Edit Bill
            </button>
          )}
          <button className={styles.actionButton} onClick={handlePrint}>
            <FiPrinter /> Print
          </button>"""

content = content.replace(old_buttons, new_buttons)

with open("frontend/src/pages/POS/InvoicePreviewPage.jsx", "w") as f:
    f.write(content)

print("Fixed buttons")

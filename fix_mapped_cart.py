import re

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "r") as f:
    content = f.read()

old_mapped = """        const mappedCart = (sale.items || []).map(item => ({
          product_id: item.product_id || item.id, 
          sku: item.sku,
          name: item.product_name || item.name,
          hsn_sac: item.hsn_sac,
          selling_price: item.rate || item.selling_price || 0,
          gst_percent: item.gst_rate || item.gst_percent || 0,
          quantity: item.quantity,
          discount: item.discount || 0
        }));"""

new_mapped = """        const mappedCart = (sale.items || []).map(item => {
          const qty = item.quantity || 1;
          const rate = item.rate || item.selling_price || 0;
          const discount = item.discount || 0;
          const gst = item.gst_rate || item.gst_percent || 0;
          const taxable = (rate * qty) - discount;
          const tax = taxable * (gst / 100);
          
          return {
            product_id: item.product_id || item.id, 
            sku: item.sku,
            name: item.product_name || item.name,
            hsn_sac: item.hsn_sac,
            selling_price: rate,
            gst_rate: gst,
            quantity: qty,
            discount: discount,
            taxable_amount: taxable,
            cgst: tax / 2,
            sgst: tax / 2,
            igst: 0,
            line_total: taxable + tax,
            unit: item.unit || 'PCS'
          };
        });"""

content = content.replace(old_mapped, new_mapped)

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "w") as f:
    f.write(content)


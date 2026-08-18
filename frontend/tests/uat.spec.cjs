const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();

  const pageA = await context.newPage(); // POS
  const pageB = await context.newPage(); // Inventory

  // 1. Login
  await pageA.goto('http://localhost:5173/login');
  await pageA.click('button[type="submit"]');
  await pageA.waitForLoadState('networkidle');

  // 2. Select BKR company (must do BEFORE navigating to POS)
  try {
    await pageA.waitForSelector('select[aria-label="Select company"]', { timeout: 5000 });
    await pageA.locator('select[aria-label="Select company"]').selectOption('2');
    await pageA.waitForTimeout(500);
    console.log('✅ Selected BKR company');
  } catch (e) {
    console.log('⚠️ Could not find company selector:', e.message);
  }

  // 3. Open POS (which is BKR-locked)
  await pageA.goto('http://localhost:5173/pos');
  await pageA.waitForLoadState('networkidle');

  // 4. Search + add product
  await pageA.fill('input[placeholder="Search by SKU or Name..."]', 'LG0905');
  await pageA.waitForTimeout(500);

  try {
    await pageA.waitForSelector('div[class*="searchItem"]', { timeout: 10000 });
    await pageA.locator('div[class*="searchItem"]').first().click();
    console.log('✅ Added LG0905 to cart');
  } catch (e) {
    console.log("❌ Timeout waiting for search item. Taking screenshot...");
    await pageA.screenshot({ path: 'pos_error.png' });
    await browser.close();
    process.exit(1);
  }

  // 5. Fill GST rate if needed
  try {
    await pageA.waitForSelector('input[class*="gstInput"]', { timeout: 2000 });
    await pageA.fill('input[class*="gstInput"]', '18');
    await pageA.waitForTimeout(500);
    console.log('✅ Filled GST rate');
  } catch (e) {
    // GST might not need confirmation
  }

  // 6. Checkout as B2C
  await pageA.getByText('B2C').click();
  
  // Intercept the sale response
  const salePromise = pageA.waitForResponse(
    resp => resp.url().includes('/api/pos/sale') && resp.status() === 200,
    { timeout: 15000 }
  );

  await pageA.click('button[class*="checkoutBtn"]');

  try {
    const saleResp = await salePromise;
    const saleData = await saleResp.json();
    console.log('✅ Sale API returned 200 OK');
    console.log('   Invoice:', saleData?.receipt?.invoice_number || 'N/A');
  } catch (e) {
    console.log('❌ FAIL: Sale API did not return 200');
    await pageA.screenshot({ path: 'sale_error.png' });
    await browser.close();
    process.exit(1);
  }

  // 7. Verify inventory changed in DB via API
  await pageA.waitForTimeout(500);
  const inventoryResp = await pageA.evaluate(async () => {
    const token = localStorage.getItem('token');
    const res = await fetch('http://localhost:8000/api/inventory/', {
      headers: { 
        'Authorization': `Bearer ${token}`,
        'X-Company-Id': '2'
      }
    });
    return await res.json();
  });

  const items = inventoryResp.data || inventoryResp;
  if (Array.isArray(items)) {
    const lg0905Items = items.filter(i => i.product_sku === 'LG0905');
    console.log(`\nFound ${lg0905Items.length} LG0905 inventory records:`);
    lg0905Items.forEach(item => {
      console.log(`  WH: ${item.warehouse_name}, ProdID: ${item.product_id}, Qty: ${item.current_qty}, Available: ${item.available_qty}`);
    });

    const anyDeducted = lg0905Items.some(i => i.current_qty < 100);
    if (anyDeducted) {
      console.log('\n✅ PASS: Inventory was deducted by the sale');
    } else {
      console.log('\n❌ FAIL: No inventory deduction detected');
    }
  } else {
    console.log('Unexpected response:', JSON.stringify(inventoryResp).slice(0, 500));
  }

  // 8. Cross-tab: open inventory in Tab B and verify it shows updated data
  await pageB.goto('http://localhost:5173/inventory');
  await pageB.waitForLoadState('networkidle');
  try {
    await pageB.waitForSelector('select[aria-label="Select company"]', { timeout: 3000 });
    await pageB.locator('select[aria-label="Select company"]').selectOption('2');
    await pageB.waitForTimeout(1000);
    
    const rows = await pageB.locator('tbody tr').allTextContents();
    const lg0905Row = rows.find(r => r.includes('LG0905'));
    if (lg0905Row) {
      console.log('\n📋 Inventory page row:', lg0905Row);
    }
  } catch (e) {
    console.log('⚠️ Could not verify inventory page');
  }

  console.log('\n🏁 UAT Complete');
  await browser.close();
})();

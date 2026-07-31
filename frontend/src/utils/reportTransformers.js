// Core join function to assemble the master dataset
export const buildJoinedDataset = (inventory, products, warehouses) => {
  const warehouseMap = warehouses.reduce((acc, wh) => {
    acc[wh.id] = wh.name;
    return acc;
  }, {});

  // Group inventory by SKU
  const invBySku = inventory.reduce((acc, inv) => {
    if (!acc[inv.product_sku]) acc[inv.product_sku] = [];
    acc[inv.product_sku].push(inv);
    return acc;
  }, {});

  const joined = [];

  products.forEach(p => {
    const invRecords = invBySku[p.sku];
    
    if (invRecords && invRecords.length > 0) {
      invRecords.forEach(inv => {
        joined.push({
          ...inv,
          product_name: p.name || 'Unknown Product',
          item_rate: p.item_rate || 0,
          min_stock_level: p.min_stock_level || 0,
          warehouse_name: warehouseMap[inv.warehouse_id] || `WH-${inv.warehouse_id}`
        });
      });
    } else {
      // Product has no inventory records anywhere
      joined.push({
        product_sku: p.sku,
        warehouse_id: null,
        available_qty: 0,
        current_qty: 0,
        reserved_qty: 0,
        product_name: p.name || 'Unknown Product',
        item_rate: p.item_rate || 0,
        min_stock_level: p.min_stock_level || 0,
        warehouse_name: 'Not Assigned'
      });
    }
  });

  return joined;
};

export const buildLowStockReport = (joinedData) => {
  const filtered = joinedData.filter(row => 
    row.available_qty < row.min_stock_level && 
    row.available_qty >= 0 && 
    row.min_stock_level > 0
  );
  
  const summary = {
    title: 'Low Stock Report',
    metrics: [
      { label: 'Products Below Min', value: filtered.length },
      { label: 'Total Units Affected', value: filtered.reduce((sum, r) => sum + r.available_qty, 0) }
    ]
  };

  const columns = [
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product Name' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'available_qty', label: 'Available Qty' },
    { key: 'min_stock_level', label: 'Min Stock' }
  ];

  return { data: filtered, summary, columns };
};

export const buildNegativeStockReport = (joinedData) => {
  const filtered = joinedData.filter(row => row.available_qty < 0);
  
  const summary = {
    title: 'Negative Inventory Report',
    metrics: [
      { label: 'Products Affected', value: filtered.length },
      { label: 'Total Negative Qty', value: filtered.reduce((sum, r) => sum + r.available_qty, 0) }
    ]
  };

  const columns = [
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product Name' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'available_qty', label: 'Negative Qty' }
  ];

  return { data: filtered, summary, columns };
};

export const buildWarehouseSummary = (joinedData, warehouses) => {
  const summaryData = warehouses.map(wh => {
    const whInv = joinedData.filter(inv => inv.warehouse_id === wh.id);
    const totalInv = whInv.reduce((sum, inv) => sum + inv.available_qty, 0);
    const lowStock = whInv.filter(inv => 
      inv.available_qty < inv.min_stock_level && 
      inv.available_qty >= 0 && 
      inv.min_stock_level > 0
    ).length;
    const negStock = whInv.filter(inv => inv.available_qty < 0).length;
    
    return {
      warehouse_name: wh.name,
      total_products: new Set(whInv.map(i => i.product_sku)).size,
      total_inventory: totalInv,
      low_stock_count: lowStock,
      negative_stock_count: negStock
    };
  });
  
  const summary = {
    title: 'Warehouse Inventory Summary',
    metrics: [
      { label: 'Total Warehouses', value: summaryData.length },
      { label: 'Total Global Inventory', value: summaryData.reduce((sum, w) => sum + w.total_inventory, 0) }
    ]
  };

  const columns = [
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'total_products', label: 'Unique Products' },
    { key: 'total_inventory', label: 'Total Inventory' },
    { key: 'low_stock_count', label: 'Low Stock Count' },
    { key: 'negative_stock_count', label: 'Negative Stock Count' }
  ];

  return { data: summaryData, summary, columns };
};

export const buildInventoryValuation = (joinedData) => {
  const valuedData = joinedData.map(row => ({
    ...row,
    inventory_value: row.available_qty * row.item_rate
  })).filter(row => row.available_qty > 0); // Valuation only for positive stock

  const totalVal = valuedData.reduce((sum, r) => sum + r.inventory_value, 0);
  
  const summary = {
    title: 'Inventory Valuation Report',
    metrics: [
      { label: 'Total Inventory Value', value: new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(totalVal) },
      { label: 'Products Valued', value: valuedData.length }
    ]
  };

  const columns = [
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product Name' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'available_qty', label: 'Available Qty' },
    { key: 'item_rate', label: 'Item Rate' },
    { 
      key: 'inventory_value', 
      label: 'Inventory Value',
      render: (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val)
    }
  ];

  return { data: valuedData, summary, columns };
};

export const buildReplenishmentReport = (joinedData) => {
  const filtered = joinedData.filter(row => 
    row.available_qty < row.min_stock_level && 
    row.min_stock_level > 0
  );
  
  const repData = filtered.map(row => ({
    ...row,
    required_qty: row.min_stock_level - row.available_qty
  }));

  const summary = {
    title: 'Daily Replenishment Report',
    metrics: [
      { label: 'Products to Replenish', value: repData.length },
      { label: 'Total Required Qty', value: repData.reduce((sum, r) => sum + r.required_qty, 0) }
    ]
  };

  const columns = [
    { key: 'product_sku', label: 'SKU' },
    { key: 'product_name', label: 'Product Name' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'available_qty', label: 'Current Qty' },
    { key: 'min_stock_level', label: 'Min Stock' },
    { key: 'required_qty', label: 'Required Qty' }
  ];

  return { data: repData, summary, columns };
};

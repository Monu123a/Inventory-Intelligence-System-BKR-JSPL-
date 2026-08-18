export const API_ROUTES = {
  AUTH: {
    LOGIN: '/api/auth/login',
    ME: '/api/auth/me',
  },
  DASHBOARD: {
    METRICS: '/api/dashboard/metrics',
    ACTIVITY: '/api/dashboard/activity',
    ALERTS: '/api/dashboard/alerts',
  },
  COMPANIES: '/api/companies',
  PRODUCTS: '/api/products',
  WAREHOUSES: '/api/warehouses',
  STATE_HUBS: '/api/state-hubs',
  WAREHOUSE_INVENTORY: '/api/warehouse-inventory',
  DELIVERY_CHALLANS: '/api/delivery-challans',
  AMAZON_RETURNS: '/api/amazon-returns',
  DAMAGE_CLAIMS: '/api/damage-claims',
  INVENTORY: {
    BASE: '/api/inventory',
    UPLOAD: '/api/inventory/upload',
    HISTORY: '/api/inventory/history',
  },
  REPORTS: {
    LOW_STOCK: '/api/reports/generate/low-stock',
    NEGATIVE_STOCK: '/api/reports/generate/negative-stock',
    REPLENISHMENT: '/api/reports/generate/daily-replenishment',
    HISTORY: '/api/reports/history',
    DOWNLOAD: '/api/reports/download',
  },
};

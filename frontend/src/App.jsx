import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from './constants/routes';
import MainLayout from './components/layout/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import NotificationManager from './components/Notification/NotificationManager';
import LoadingOverlay from './components/LoadingOverlay/LoadingOverlay';
import ErrorBoundary from './components/ErrorBoundary/ErrorBoundary';

const Overview = lazy(() => import('./pages/Overview/Overview'));
const Products = lazy(() => import('./pages/Products/Products'));
const Warehouses = lazy(() => import('./pages/Warehouses/Warehouses'));
const Inventory = lazy(() => import('./pages/Inventory/Inventory'));
const InventoryHistory = lazy(() => import('./pages/InventoryHistory/InventoryHistory'));
const Reports = lazy(() => import('./pages/Reports/Reports'));
const DownloadCentre = lazy(() => import('./pages/DownloadCentre/DownloadCentre'));
const Login = lazy(() => import('./pages/Login/Login'));
const Settings = lazy(() => import('./pages/Settings/SettingsPage'));
const POSPage = lazy(() => import('./pages/POS/POSPage'));
const SalesHistoryPage = lazy(() => import('./pages/POS/SalesHistoryPage'));
const InvoicePreviewPage = lazy(() => import('./pages/POS/InvoicePreviewPage'));

const JSPLReplenishmentView = lazy(() => import('./pages/Replenishment/JSPLReplenishmentView'));
const BKRRequirementsView = lazy(() => import('./pages/Replenishment/BKRRequirementsView'));
const BKRInvoiceGenerator = lazy(() => import('./pages/Replenishment/BKRInvoiceGenerator'));
const InterCompanyHistory = lazy(() => import('./pages/Replenishment/InterCompanyHistory'));
const App = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center' }}>Loading Application...</div>}>
          <NotificationManager />
          <LoadingOverlay />
          <Routes>
            {/* Public Routes */}
            <Route path={ROUTES.LOGIN} element={<Login />} />
            
            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path={ROUTES.OVERVIEW} element={<Overview />} />
                <Route path={ROUTES.PRODUCTS} element={<Products />} />
                <Route path={ROUTES.WAREHOUSES} element={<Warehouses />} />
                <Route path={ROUTES.INVENTORY} element={<Inventory />} />
                <Route path={ROUTES.INVENTORY_HISTORY} element={<InventoryHistory />} />
                <Route path={ROUTES.REPORTS} element={<Reports />} />
                <Route path={ROUTES.DOWNLOAD_CENTRE} element={<DownloadCentre />} />
                <Route path={ROUTES.SETTINGS} element={<Settings />} />
                <Route path={ROUTES.POS} element={<POSPage />} />
                <Route path={ROUTES.POS_HISTORY} element={<SalesHistoryPage />} />
                <Route path={ROUTES.POS_INVOICE} element={<InvoicePreviewPage />} />
                <Route path={ROUTES.REPLENISHMENT_JSPL} element={<JSPLReplenishmentView />} />
                <Route path={ROUTES.REPLENISHMENT_BKR} element={<BKRRequirementsView />} />
                <Route path={ROUTES.REPLENISHMENT_BKR_INVOICE} element={<BKRInvoiceGenerator />} />
                <Route path={ROUTES.INTER_COMPANY_HISTORY} element={<InterCompanyHistory />} />
              </Route>
            </Route>
            
            <Route path="*" element={<Navigate to={ROUTES.OVERVIEW} replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;

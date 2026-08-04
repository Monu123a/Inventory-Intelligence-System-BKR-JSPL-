import React from 'react';
import PageContainer from '../../components/layout/PageContainer';
import Button from '../../components/forms/Button';
import { MetricCard } from '../../components/MetricCard/MetricCard';
import { SystemHealthCard } from './components/SystemHealthCard';
import { RecentActivity } from './components/RecentActivity';
import { AlertsPanel } from './components/AlertsPanel';
import { ROUTES } from '../../constants/routes';
import { useDashboardMetrics, useDashboardActivity, useDashboardAlerts, useReturnMetrics } from '../../hooks/useDashboard';
import useCompanyStore from '../../stores/useCompanyStore';
import { FiBox, FiLayers, FiDatabase, FiAlertCircle, FiTrendingDown, FiBell, FiRefreshCw, FiShoppingCart, FiDollarSign, FiRefreshCcw, FiClock, FiCheckCircle, FiXCircle, FiFileText } from 'react-icons/fi';
import styles from './Overview.module.css';
import { useQueryClient } from '@tanstack/react-query';

const DashboardSkeleton = () => (
  <div className={styles.skeletonContainer}>
    <div className={styles.kpiGrid}>
      {[...Array(6)].map((_, i) => <div key={i} className={styles.skeletonCard} />)}
    </div>
    <div className={styles.row2}>
      <div className={styles.skeletonCard} style={{ height: '300px' }} />
      <div className={styles.skeletonCard} style={{ height: '300px' }} />
    </div>
  </div>
);

const Overview = () => {
  const queryClient = useQueryClient();
  const { currentCompany } = useCompanyStore();
  const isBkr = currentCompany?.code === 'BKR';
  
  const { data: metricsData, isPending: metricsPending, error: metricsError } = useDashboardMetrics();
  const { data: returnData, isPending: returnPending } = useReturnMetrics();
  const { data: activityData, isPending: activityPending, error: activityError } = useDashboardActivity();
  const { data: alertsData, isPending: alertsPending, error: alertsError } = useDashboardAlerts();

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  if (metricsPending || activityPending || alertsPending || returnPending) {
    return (
      <PageContainer title="Overview Dashboard">
        <DashboardSkeleton />
      </PageContainer>
    );
  }

  if (metricsError || activityError || alertsError) {
    return (
      <PageContainer
        title="Overview Dashboard"
        actions={
          <Button variant="secondary" onClick={handleRefresh}>
            <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
          </Button>
        }
      >
        <div className={styles.skeletonContainer}>
          <div className={styles.skeletonCard} style={{ height: 'auto', padding: '24px' }}>
            Dashboard data could not be loaded. Please refresh the page or try again after restarting the backend.
          </div>
        </div>
      </PageContainer>
    );
  }

  const kpis = metricsData?.kpis;
  const health = metricsData?.health;
  const recentActivity = activityData?.recent_activity;
  const recentAlerts = alertsData?.recent_alerts;

  return (
    <PageContainer 
      title="Overview Dashboard"
      actions={
        <Button variant="secondary" onClick={handleRefresh}>
          <FiRefreshCw style={{ marginRight: '8px' }} /> Refresh
        </Button>
      }
    >
      <div className={styles.kpiGrid}>
        <MetricCard 
          title="Total Products" 
          value={kpis?.total_products ?? 0} 
          icon={FiBox} 
          color="primary"
          navigateTo={ROUTES.PRODUCTS}
        />
        <MetricCard 
          title="Total Warehouses" 
          value={kpis?.total_warehouses ?? 0} 
          icon={FiLayers} 
          color="primary"
          navigateTo={ROUTES.WAREHOUSES}
        />
        <MetricCard 
          title="Total Inventory Qty" 
          value={kpis?.total_inventory ?? 0} 
          icon={FiDatabase} 
          color="primary"
          navigateTo={ROUTES.INVENTORY}
        />
        <MetricCard 
          title="Negative Stock" 
          value={kpis?.negative_stock_products ?? 0} 
          icon={FiAlertCircle} 
          color="danger"
          navigateTo={ROUTES.INVENTORY}
        />
        
        {isBkr && (
          <>
            <MetricCard 
              title="Today's Offline Revenue" 
              value={`₹${(kpis?.pos_revenue_today ?? 0).toFixed(2)}`}
              icon={FiDollarSign} 
              color="primary"
              navigateTo={ROUTES.POS_HISTORY}
            />
            <MetricCard 
              title="Today's Offline Sales" 
              value={kpis?.pos_sales_count_today ?? 0}
              icon={FiShoppingCart} 
              color="primary"
              navigateTo={ROUTES.POS_HISTORY}
            />
            <MetricCard 
              title="Products Sold (Offline)" 
              value={kpis?.pos_products_sold_today ?? 0}
              icon={FiBox} 
              color="primary"
              navigateTo={ROUTES.POS_HISTORY}
            />
            <MetricCard 
              title="Sales Returns Today" 
              value={kpis?.sales_returns_today ?? 0}
              icon={FiRefreshCcw} 
              color="warning"
              navigateTo={ROUTES.SALES_RETURNS}
            />
            <MetricCard 
              title="Return Value Today" 
              value={`₹${(kpis?.sales_return_value_today ?? 0).toFixed(2)}`}
              icon={FiDollarSign} 
              color="danger"
              navigateTo={ROUTES.SALES_RETURNS}
            />
            <MetricCard 
              title="Pending Returns" 
              value={kpis?.pending_sales_returns ?? 0}
              icon={FiClock} 
              color="warning"
              navigateTo={ROUTES.SALES_RETURNS}
            />
            <MetricCard 
              title="Challans Today" 
              value={kpis?.challans_today ?? 0}
              icon={FiFileText} 
              color="primary"
              navigateTo={ROUTES.DELIVERY_CHALLANS}
            />
          </>
        )}

        <MetricCard 
          title="Low Stock" 
          value={kpis?.low_stock_products ?? 0} 
          icon={FiTrendingDown} 
          color="warning"
          navigateTo={`${ROUTES.REPORTS}?type=replenishment`}
        />
        <MetricCard 
          title="Active Alerts" 
          value={kpis?.active_alerts ?? 0} 
          icon={FiBell} 
          color={kpis?.active_alerts > 0 ? "danger" : "success"}
        />

        {/* Return Metrics */}
        <MetricCard 
          title="Returns Today" 
          value={returnData?.returns_today ?? 0} 
          icon={FiRefreshCcw} 
          color="primary"
          navigateTo={ROUTES.AMAZON_RETURNS}
        />
        <MetricCard 
          title="Awaiting Inspection" 
          value={returnData?.awaiting_inspection ?? 0} 
          icon={FiClock} 
          color="warning"
          navigateTo={ROUTES.AMAZON_RETURNS}
        />
        <MetricCard 
          title="Restocked" 
          value={returnData?.restocked ?? 0} 
          icon={FiCheckCircle} 
          color="success"
          navigateTo={ROUTES.AMAZON_RETURNS}
        />
        <MetricCard 
          title="Defective" 
          value={returnData?.defective ?? 0} 
          icon={FiXCircle} 
          color="danger"
          navigateTo={ROUTES.DEFECTIVE_INVENTORY}
        />
        <MetricCard 
          title="Pending > 2 Days" 
          value={returnData?.inspection_pending_old ?? 0} 
          icon={FiAlertCircle} 
          color="danger"
          navigateTo={ROUTES.AMAZON_RETURNS}
        />
      </div>

      <div className={styles.row2}>
        <div className={styles.healthCol}>
          <SystemHealthCard health={health} />
        </div>
        <div className={styles.alertsCol}>
          <AlertsPanel alerts={recentAlerts} />
        </div>
      </div>

      <div className={styles.row3}>
        <RecentActivity activities={recentActivity} />
      </div>

    </PageContainer>
  );
};

export default Overview;

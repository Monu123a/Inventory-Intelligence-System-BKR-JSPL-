import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import { useUIStore } from '../../stores/uiStore';
import useCompanyStore from '../../stores/useCompanyStore';
import { FiHome, FiBox, FiLayers, FiList, FiClock, FiFileText, FiDownload, FiSettings, FiShoppingCart, FiDollarSign, FiRefreshCw, FiRepeat } from 'react-icons/fi';
import styles from './Sidebar.module.css';

const navItems = [
  { path: ROUTES.OVERVIEW, label: 'Overview', icon: FiHome },
  { path: ROUTES.PRODUCTS, label: 'Products', icon: FiBox },
  { path: ROUTES.WAREHOUSES, label: 'Warehouses', icon: FiLayers },
  { path: ROUTES.INVENTORY, label: 'Inventory', icon: FiList },
  { path: ROUTES.DEFECTIVE_INVENTORY, label: 'Defective Inventory', icon: FiBox },
  { path: ROUTES.AMAZON_RETURNS, label: 'Amazon Returns', icon: FiBox },
  { path: ROUTES.INVENTORY_HISTORY, label: 'Inventory History', icon: FiClock },
  { path: ROUTES.INTER_COMPANY_HISTORY, label: 'Inter-Company History', icon: FiRepeat },
  { path: ROUTES.REPORTS, label: 'Reports', icon: FiFileText },
  { path: ROUTES.DOWNLOAD_CENTRE, label: 'Download Centre', icon: FiDownload },
];

const Sidebar = () => {
  const { isSidebarOpen } = useUIStore();
  const { currentCompany } = useCompanyStore();
  const [isWarehouseOpen, setIsWarehouseOpen] = useState(false);
  const [isLogisticsOpen, setIsLogisticsOpen] = useState(false);
  
  const isBkr = currentCompany?.code === 'BKR';

  return (
    <aside className={`${styles.sidebar} ${isSidebarOpen ? styles.open : styles.closed}`}>
      <div className={styles.header}>
        <h1 className={styles.logo}>{currentCompany ? currentCompany.name : 'Inventory'}</h1>
      </div>
      
      <nav className={styles.nav}>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
          >
            <item.icon className={styles.icon} />
            <span className={styles.label}>{item.label}</span>
          </NavLink>
        ))}

        {!isBkr ? (
          <NavLink
            to={ROUTES.REPLENISHMENT_JSPL}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
          >
            <FiRefreshCw className={styles.icon} />
            <span className={styles.label}>Need Replenishment</span>
          </NavLink>
        ) : (
          <NavLink
            to={ROUTES.REPLENISHMENT_BKR}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
          >
            <FiRefreshCw className={styles.icon} />
            <span className={styles.label}>JSPL Requirements</span>
          </NavLink>
        )}


        {isBkr && (
          <>
            <div className={styles.divider}></div>
            <NavLink
              to={ROUTES.POS}
              className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
            >
              <FiShoppingCart className={styles.icon} />
              <span className={styles.label}>Offline Sales</span>
            </NavLink>
            <NavLink
              to={ROUTES.POS_HISTORY}
              className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
            >
              <FiDollarSign className={styles.icon} />
              <span className={styles.label}>Sales History</span>
            </NavLink>
            <NavLink
              to={ROUTES.SALES_RETURNS}
              className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
            >
              <FiRefreshCw className={styles.icon} />
              <span className={styles.label}>Sales Returns</span>
            </NavLink>
            <NavLink
              to={ROUTES.DELIVERY_CHALLANS}
              className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
            >
              <FiFileText className={styles.icon} />
              <span className={styles.label}>Delivery Challans</span>
            </NavLink>
          </>
        )}

        <div className={styles.divider}></div>
        <div className={styles.sectionHeader}>Service</div>
        <NavLink to={ROUTES.SERVICE_DASHBOARD} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Service Dashboard</span>
        </NavLink>
        <NavLink to={ROUTES.SERVICE_CREATE} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>New Service</span>
        </NavLink>
        <NavLink to={ROUTES.SERVICE_RECORDS} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Service Records</span>
        </NavLink>
        <NavLink to={ROUTES.SERVICE_HISTORY} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Service History</span>
        </NavLink>
        <NavLink to={ROUTES.SERVICE_REMINDERS} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Service Reminders</span>
        </NavLink>

        <div className={styles.divider}></div>
        
        {/* Warehouse Phase 8 Section */}
        <div 
          className={styles.sectionHeader} 
          onClick={() => setIsWarehouseOpen(!isWarehouseOpen)}
          style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
        >
          Warehouse {isWarehouseOpen ? '▼' : '▶'}
        </div>
        {isWarehouseOpen && (
          <>
            <NavLink to={ROUTES.WAREHOUSE_DASHBOARD} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Dashboard</span>
            </NavLink>
            <NavLink to={ROUTES.WAREHOUSE_STATE_HUBS} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>State Hubs</span>
            </NavLink>
            <NavLink to={ROUTES.WAREHOUSE_MASTER_LIST} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Master List</span>
            </NavLink>
            <NavLink to={ROUTES.WAREHOUSE_INVENTORY} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Inventory</span>
            </NavLink>
          </>
        )}

        <div className={styles.divider}></div>

        {/* Logistics Section */}
        <div 
          className={styles.sectionHeader} 
          onClick={() => setIsLogisticsOpen(!isLogisticsOpen)}
          style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
        >
          Logistics {isLogisticsOpen ? '▼' : '▶'}
        </div>
        {isLogisticsOpen && (
          <>
            <NavLink to={ROUTES.LOGISTICS_DISPATCH_DASHBOARD} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Dispatch Dashboard</span>
            </NavLink>
            <NavLink to={ROUTES.LOGISTICS_BATCH_DISPATCH} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Batch Dispatch</span>
            </NavLink>
            <NavLink to={ROUTES.LOGISTICS_RETURNS} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>FC Returns</span>
            </NavLink>
            <NavLink to={ROUTES.LOGISTICS_DAMAGE_CLAIMS} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Damage Claims</span>
            </NavLink>
            <NavLink to={ROUTES.LOGISTICS_RETURN_RECOMMENDATIONS} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              <span className={styles.label}>Return Recommendations</span>
            </NavLink>
          </>
        )}

        <div className={styles.divider}></div>
        <div className={styles.sectionHeader}>Accounting</div>
        <NavLink to={ROUTES.ACCOUNTING_EXPORT_CENTER} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Export Center</span>
        </NavLink>
        <NavLink to={ROUTES.ACCOUNTING_MASTER_SYNC} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Master Sync</span>
        </NavLink>
        <NavLink to={ROUTES.ACCOUNTING_HISTORY} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Export History</span>
        </NavLink>
        <NavLink to={ROUTES.ACCOUNTING_MAPPING} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Mapping</span>
        </NavLink>
        <NavLink to={ROUTES.ACCOUNTING_CONFIG} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
          <span className={styles.label}>Configuration</span>
        </NavLink>

      </nav>

      <div className={styles.footer}>
        <NavLink
          to={ROUTES.SETTINGS}
          className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
        >
          <FiSettings className={styles.icon} />
          <span className={styles.label}>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
};

export default Sidebar;

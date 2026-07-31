import React from 'react';
import { NavLink } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import { useUIStore } from '../../stores/uiStore';
import useCompanyStore from '../../stores/useCompanyStore';
import { FiHome, FiBox, FiLayers, FiList, FiClock, FiFileText, FiDownload, FiSettings, FiShoppingCart, FiDollarSign } from 'react-icons/fi';
import styles from './Sidebar.module.css';

const navItems = [
  { path: ROUTES.OVERVIEW, label: 'Overview', icon: FiHome },
  { path: ROUTES.PRODUCTS, label: 'Products', icon: FiBox },
  { path: ROUTES.WAREHOUSES, label: 'Warehouses', icon: FiLayers },
  { path: ROUTES.INVENTORY, label: 'Inventory', icon: FiList },
  { path: ROUTES.INVENTORY_HISTORY, label: 'Inventory History', icon: FiClock },
  { path: ROUTES.REPORTS, label: 'Reports', icon: FiFileText },
  { path: ROUTES.DOWNLOAD_CENTRE, label: 'Download Centre', icon: FiDownload },
];

const Sidebar = () => {
  const { isSidebarOpen } = useUIStore();
  const { currentCompany } = useCompanyStore();
  
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
          </>
        )}
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

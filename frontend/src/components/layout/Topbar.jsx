import React from 'react';
import { useAuthStore } from '../../stores/authStore';
import { useUIStore } from '../../stores/uiStore';
import { FiMenu, FiBell, FiLogOut } from 'react-icons/fi';
import styles from './Topbar.module.css';
import { useNavigate } from 'react-router-dom';
import CompanySelector from '../common/CompanySelector';

const Topbar = () => {
  const { toggleSidebar } = useUIStore();
  const { logout, user } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <button className={styles.iconBtn} onClick={toggleSidebar}>
          <FiMenu />
        </button>
        <h2 className={styles.title}>Inventory Intelligence System</h2>
      </div>
      
      <div className={styles.right}>
        <CompanySelector />
        <button className={styles.iconBtn}>
          <FiBell />
        </button>
        <div className={styles.userProfile}>
          <span className={styles.userName}>{user?.name || 'Admin User'}</span>
          <div className={styles.avatar}>
            {user?.name ? user.name.charAt(0).toUpperCase() : 'A'}
          </div>
        </div>
        <button className={styles.iconBtn} onClick={handleLogout} title="Logout">
          <FiLogOut />
        </button>
      </div>
    </header>
  );
};

export default Topbar;

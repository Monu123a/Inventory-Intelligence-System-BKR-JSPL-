import React, { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import styles from './MainLayout.module.css';

const PageLoader = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '60vh',
    color: '#64748b',
    fontSize: '14px',
    fontWeight: 500,
    gap: '12px'
  }}>
    <div style={{
      width: '24px',
      height: '24px',
      border: '3px solid #e2e8f0',
      borderTopColor: '#3b82f6',
      borderRadius: '50%',
      animation: 'mainLayoutSpin 0.7s linear infinite'
    }} />
    <span>Loading page...</span>
    <style>{`@keyframes mainLayoutSpin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
  </div>
);

const MainLayout = () => {
  return (
    <div className={styles.layout}>
      <Sidebar />
      <div className={styles.contentWrapper}>
        <Topbar />
        <main className={styles.main}>
          <div className={styles.pageContent}>
            <Suspense fallback={<PageLoader />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
};

export default MainLayout;

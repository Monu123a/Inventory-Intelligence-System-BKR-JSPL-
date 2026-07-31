import React from 'react';
import styles from './SettingsPage.module.css';
import useCompanyStore from '../../stores/useCompanyStore';

const SettingsPage = () => {
  const { companyCode } = useCompanyStore();

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
        <p className={styles.subtitle}>Manage configuration for {companyCode}</p>
      </div>
      
      <div className={styles.content}>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>General Settings</h2>
          <p className={styles.description}>
            General configuration options are currently managed by administrators. 
            More self-service settings will be available in future updates.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;

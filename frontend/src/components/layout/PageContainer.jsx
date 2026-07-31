import React from 'react';
import styles from './PageContainer.module.css';

const PageContainer = ({ title, children, actions }) => {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>{title}</h1>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      <div className={styles.content}>
        {children}
      </div>
    </div>
  );
};

export default PageContainer;

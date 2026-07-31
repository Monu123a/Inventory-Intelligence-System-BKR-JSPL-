import React from 'react';
import { useUIStore } from '../../stores/uiStore';
import styles from './LoadingOverlay.module.css';

const LoadingOverlay = () => {
  const { isLoadingOverlayActive, loadingOverlayMessage } = useUIStore();

  if (!isLoadingOverlayActive) return null;

  return (
    <div className={styles.overlay}>
      <div className={styles.spinnerWrapper}>
        <div className={styles.spinner}></div>
        {loadingOverlayMessage && <p className={styles.message}>{loadingOverlayMessage}</p>}
      </div>
    </div>
  );
};

export default LoadingOverlay;

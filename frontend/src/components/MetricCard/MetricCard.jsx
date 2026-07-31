import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../Card/Card';
import styles from './MetricCard.module.css';

export const MetricCard = ({ title, value, icon: Icon, color = 'primary', navigateTo, className = '' }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (navigateTo) {
      navigate(navigateTo);
    }
  };

  return (
    <div 
      className={`${styles.metricWrapper} ${navigateTo ? styles.clickable : ''} ${className}`}
      onClick={handleClick}
    >
      <Card>
        <div className={styles.container}>
          <div className={styles.content}>
            <p className={styles.title}>{title}</p>
            <h4 className={styles.value}>{value}</h4>
          </div>
          {Icon && (
            <div className={`${styles.iconWrapper} ${styles[`icon--${color}`]}`}>
              <Icon className={styles.icon} />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

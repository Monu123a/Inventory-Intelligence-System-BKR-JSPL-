import React from 'react';
import { useNotificationStore } from '../../stores/notificationStore';
import styles from './NotificationManager.module.css';

const NotificationManager = () => {
  const { notifications, removeNotification } = useNotificationStore();

  return (
    <div className={styles.container}>
      {notifications.map((notif) => (
        <div key={notif.id} className={`${styles.toast} ${styles[`toast--${notif.type || 'info'}`]}`}>
          <div className={styles.content}>
            {notif.title && <h4 className={styles.title}>{notif.title}</h4>}
            <p className={styles.message}>{notif.message}</p>
          </div>
          <button className={styles.closeBtn} onClick={() => removeNotification(notif.id)}>&times;</button>
        </div>
      ))}
    </div>
  );
};

export default NotificationManager;

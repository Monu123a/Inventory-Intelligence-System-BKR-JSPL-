import { useNotificationStore } from '../stores/notificationStore';

/**
 * Standardized API Error Handler
 * Maps HTTP status codes to standard UI behaviors and notifications.
 * @param {Error} err - The error caught from axios/api request
 * @param {string} fallbackMsg - A fallback message if the backend didn't provide one
 */
export const handleApiError = (err, fallbackMsg = 'Something failed') => {
  const status = err.response?.status;
  const detail = err.response?.data?.detail;
  const message = detail || err.message || fallbackMsg;
  
  const addNotification = useNotificationStore.getState().addNotification;

  switch (status) {
    case 401:
      addNotification({
        type: 'error',
        title: 'Session Expired',
        message: 'Please log in again.',
        persist: true
      });
      // Handle logout if needed
      break;
      
    case 403:
      addNotification({
        type: 'error',
        title: 'Access Denied',
        message: 'You do not have permission to perform this action.',
      });
      break;
      
    case 409:
      addNotification({
        type: 'error',
        title: 'Business Conflict',
        message: typeof message === 'string' ? message : 'Conflict occurred',
      });
      break;
      
    case 422:
      // In FastAPI, 422 might have an array of details
      const valMessage = Array.isArray(detail) 
        ? detail.map(d => `${d.loc?.join('.')} ${d.msg}`).join(', ') 
        : (typeof message === 'string' ? message : 'Validation Error');
      
      addNotification({
        type: 'error',
        title: 'Validation Error',
        message: valMessage,
      });
      break;
      
    default:
      addNotification({
        type: 'error',
        title: 'Error',
        message: typeof message === 'string' ? message : 'An unexpected error occurred',
      });
      break;
  }
};

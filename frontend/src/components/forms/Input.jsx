import React, { forwardRef } from 'react';
import styles from './Input.module.css';

const Input = forwardRef(({ label, error, className = '', ...props }, ref) => {
  return (
    <div className={`${styles.wrapper} ${className}`}>
      {label && <label className={styles.label}>{label}</label>}
      <input 
        ref={ref}
        className={`${styles.input} ${error ? styles['input--error'] : ''}`}
        {...props}
      />
      {error && <span className={styles.error}>{error.message || error}</span>}
    </div>
  );
});

Input.displayName = 'Input';
export default Input;

import React from 'react';
import styles from './Button.module.css';

const Button = ({ children, variant = 'primary', size = 'md', className = '', isLoading, ...props }) => {
  const baseClass = styles.btn;
  const variantClass = styles[`btn--${variant}`];
  const sizeClass = styles[`btn--${size}`];
  const loadingClass = isLoading ? styles['btn--loading'] : '';

  return (
    <button 
      className={`${baseClass} ${variantClass} ${sizeClass} ${loadingClass} ${className}`}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading ? <span className={styles.spinner}></span> : null}
      <span className={styles.content}>{children}</span>
    </button>
  );
};

export default Button;

import React, { useState, useEffect } from 'react';
import { FiSearch } from 'react-icons/fi';
import styles from './SearchBar.module.css';

export const SearchBar = ({ onSearch, value = '', placeholder = 'Search...', debounceMs = 300 }) => {
  const [internalValue, setInternalValue] = useState(value);

  // Sync internal state when external value prop changes
  useEffect(() => {
    setInternalValue(value);
  }, [value]);

  useEffect(() => {
    const handler = setTimeout(() => {
      onSearch(internalValue);
    }, debounceMs);

    return () => clearTimeout(handler);
  }, [internalValue, debounceMs, onSearch]);

  return (
    <div className={styles.wrapper}>
      <FiSearch className={styles.icon} />
      <input 
        type="text" 
        className={styles.input} 
        placeholder={placeholder}
        value={internalValue}
        onChange={(e) => setInternalValue(e.target.value)}
      />
    </div>
  );
};

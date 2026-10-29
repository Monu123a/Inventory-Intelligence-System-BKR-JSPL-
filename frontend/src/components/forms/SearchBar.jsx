import React, { useState, useEffect, useRef } from 'react';
import { FiSearch } from 'react-icons/fi';
import styles from './SearchBar.module.css';

export const SearchBar = ({ onSearch, onChange, value = '', placeholder = 'Search...', debounceMs = 300 }) => {
  const [internalValue, setInternalValue] = useState(value);
  const onSearchRef = useRef(onSearch || onChange);
  const lastEmittedRef = useRef(value);

  useEffect(() => {
    onSearchRef.current = onSearch || onChange;
  }, [onSearch, onChange]);

  // Sync internal state when external value prop changes
  useEffect(() => {
    if (value !== internalValue) {
      setInternalValue(value);
      lastEmittedRef.current = value;
    }
  }, [value]);

  useEffect(() => {
    // Only fire search if internalValue has actually changed from what was last emitted
    if (internalValue === lastEmittedRef.current) return;

    const handler = setTimeout(() => {
      lastEmittedRef.current = internalValue;
      if (onSearchRef.current) {
        onSearchRef.current(internalValue);
      }
    }, debounceMs);

    return () => clearTimeout(handler);
  }, [internalValue, debounceMs]);

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

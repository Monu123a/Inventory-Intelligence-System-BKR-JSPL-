import useCompanyStore from '../stores/useCompanyStore';
import { useState, useMemo, useEffect, useCallback } from 'react';
import { useNotificationStore } from '../stores/notificationStore';

const STORAGE_VERSION = '1.0';

const getStorageKey = (companyId) => `company_${companyId}_download_history`;

export const useDownloadHistory = ({ search = '', reportTypeFilter = '', page = 1, limit = 15 }) => {
  const companyId = useCompanyStore((state) => state.companyId);
  const storageKey = getStorageKey(companyId);
  const [rawHistory, setRawHistory] = useState([]);
  const [isError, setIsError] = useState(false);
  const { addNotification } = useNotificationStore.getState();

  const loadHistory = useCallback(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.version === STORAGE_VERSION && Array.isArray(parsed.history)) {
          setRawHistory(parsed.history);
          setIsError(false);
          return;
        }
      }
      setRawHistory([]);
      setIsError(false);
    } catch (e) {
      setIsError(true);
      console.error("Failed to parse download history:", e);
    }
  }, [storageKey]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory, companyId]); // Re-load when company switches

  const clearHistory = () => {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: STORAGE_VERSION, history: [] }));
      setRawHistory([]);
      addNotification({ type: 'success', title: 'History Cleared', message: 'Download history has been reset.' });
    } catch {
      addNotification({ type: 'error', title: 'Clear Failed', message: 'Could not clear history.' });
    }
  };

  const removeHistoryItem = (id) => {
    try {
      const updated = rawHistory.filter(item => item.id !== id);
      localStorage.setItem(storageKey, JSON.stringify({ version: STORAGE_VERSION, history: updated }));
      setRawHistory(updated);
    } catch {
      addNotification({ type: 'error', title: 'Remove Failed', message: 'Could not remove item.' });
    }
  };

  const resetCorruptedHistory = () => {
    clearHistory();
    setIsError(false);
  };

  const processedData = useMemo(() => {
    let filtered = [...rawHistory];

    // Search by Filename or Report Type
    if (search) {
      const lower = search.toLowerCase();
      filtered = filtered.filter(item => 
        (item.filename || '').toLowerCase().includes(lower) ||
        (item.reportType || '').toLowerCase().includes(lower)
      );
    }

    // Filter by exact Report Type
    if (reportTypeFilter) {
      filtered = filtered.filter(item => item.reportType === reportTypeFilter);
    }

    // Sort by generatedAt Descending (newest first)
    filtered.sort((a, b) => new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime());

    const totalCount = filtered.length;
    const startIndex = (page - 1) * limit;
    const paginated = filtered.slice(startIndex, startIndex + limit);

    return {
      data: paginated,
      totalCount,
      totalPages: Math.ceil(totalCount / limit)
    };
  }, [rawHistory, search, reportTypeFilter, page, limit]);

  return {
    isError,
    loadHistory,
    clearHistory,
    removeHistoryItem,
    resetCorruptedHistory,
    ...processedData
  };
};

export const saveDownloadMetadata = (metadata) => {
  try {
    const companyId = useCompanyStore.getState().companyId;
    const storageKey = getStorageKey(companyId);
    let currentHistory = [];
    const stored = localStorage.getItem(storageKey);
    
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed.version === STORAGE_VERSION && Array.isArray(parsed.history)) {
        currentHistory = parsed.history;
      }
    }

    const newRecord = {
      id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2),
      generatedAt: new Date().toISOString(),
      fileFormat: 'CSV',
      status: 'Metadata Only',
      exportVersion: '1.0',
      appVersion: '10.0',
      ...metadata
    };

    currentHistory.unshift(newRecord); // Add to beginning
    
    // Keep a cap of 500 records to prevent localStorage overflow
    if (currentHistory.length > 500) {
      currentHistory = currentHistory.slice(0, 500);
    }

    localStorage.setItem(storageKey, JSON.stringify({ version: STORAGE_VERSION, history: currentHistory }));
  } catch (e) {
    console.error("Failed to save download metadata:", e);
  }
};

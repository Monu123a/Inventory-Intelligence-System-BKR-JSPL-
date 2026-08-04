import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';
import { useNotificationStore } from '../../stores/notificationStore';
import styles from './Returns.module.css';

const AmazonReturns = () => {
    const [statusFilter, setStatusFilter] = useState('');
    const [search, setSearch] = useState('');
    const [inspectingReturn, setInspectingReturn] = useState(null);
    const [inspectionDecision, setInspectionDecision] = useState('RESTOCK');
    const [inspectionNotes, setInspectionNotes] = useState('');
    
    const queryClient = useQueryClient();
    const addNotification = useNotificationStore(state => state.addNotification);

    const { data: returns = [], isLoading } = useQuery({
        queryKey: ['amazonReturns', statusFilter, search],
        queryFn: async () => {
            const params = {};
            if (statusFilter) params.status = statusFilter;
            if (search) params.search = search;
            const res = await api.get('/api/amazon-returns/', { params });
            return res.data;
        }
    });

    const { data: syncStatus } = useQuery({
        queryKey: ['amazonReturnsSyncStatus'],
        queryFn: async () => {
            const res = await api.get('/api/amazon-returns/status');
            return res.data;
        },
        refetchInterval: 10000 // poll every 10s
    });

    const manualSyncMutation = useMutation({
        mutationFn: async () => {
            const res = await api.post('/api/amazon-returns/sync');
            return res.data;
        },
        onSuccess: () => {
            addNotification('Manual sync completed successfully', 'success');
            queryClient.invalidateQueries(['amazonReturns']);
            queryClient.invalidateQueries(['amazonReturnsSyncStatus']);
        },
        onError: (err) => {
            addNotification(err.response?.data?.detail || 'Failed to sync returns', 'error');
        }
    });

    const handleSync = () => {
        manualSyncMutation.mutate();
    };

    const inspectMutation = useMutation({
        mutationFn: async ({ returnId, data }) => {
            const res = await api.post(`/api/amazon-returns/${returnId}/inspect`, data);
            return res.data;
        },
        onSuccess: (data) => {
            addNotification(`Successfully inspected and ${data.inspection_status}`, 'success');
            setInspectingReturn(null);
            setInspectionNotes('');
            setInspectionDecision('RESTOCK');
            queryClient.invalidateQueries(['amazonReturns']);
        },
        onError: (err) => {
            addNotification(err.response?.data?.detail || 'Failed to inspect return', 'error');
        }
    });

    const handleInspectSubmit = (e) => {
        e.preventDefault();
        if (!inspectingReturn) return;
        inspectMutation.mutate({
            returnId: inspectingReturn.id,
            data: {
                decision: inspectionDecision,
                notes: inspectionNotes,
                images: []
            }
        });
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div>
                    <h2>Amazon Returns</h2>
                    <p className={styles.subtitle}>Synchronize and view Amazon customer returns.</p>
                </div>
                <div className={styles.actions}>
                    <div className={styles.syncStatus}>
                        <span>Last Sync: {syncStatus?.last_run ? new Date(syncStatus.last_run).toLocaleString() : 'Never'}</span>
                        <span className={`${styles.statusBadge} ${styles[syncStatus?.status?.toLowerCase() || 'unknown']}`}>
                            {syncStatus?.status || 'Unknown'}
                        </span>
                    </div>
                    <button 
                        className={styles.syncButton} 
                        onClick={handleSync}
                        disabled={manualSyncMutation.isLoading}
                    >
                        {manualSyncMutation.isLoading ? 'Syncing...' : 'Sync Now'}
                    </button>
                </div>
            </div>

            <div className={styles.filters}>
                <input 
                    type="text" 
                    placeholder="Search Order, Return ID or Product..." 
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className={styles.searchInput}
                />
                <select 
                    value={statusFilter} 
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className={styles.selectInput}
                >
                    <option value="">All Statuses</option>
                    <option value="In Transit">In Transit</option>
                    <option value="Received">Received</option>
                </select>
            </div>

            <div className={styles.tableContainer}>
                {isLoading ? (
                    <div className={styles.loading}>Loading returns...</div>
                ) : returns.length === 0 ? (
                    <div className={styles.empty}>No Amazon returns found.</div>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>Return ID</th>
                                <th>Amazon Order</th>
                                <th>SKU</th>
                                <th>Quantity</th>
                                <th>Return Reason</th>
                                <th>Status</th>
                                <th>Inspection Status</th>
                                <th>Requested Date</th>
                                <th>Received Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {returns.map(ret => (
                                <tr key={ret.id}>
                                    <td>{ret.amazon_return_id}</td>
                                    <td>{ret.amazon_order_id}</td>
                                    <td>{ret.sku}</td>
                                    <td>{ret.quantity}</td>
                                    <td>{ret.return_reason}</td>
                                    <td>
                                        <span className={`${styles.badge} ${styles[ret.return_status.replace(' ', '')]}`}>
                                            {ret.return_status}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`${styles.badge} ${styles[ret.inspection_status || 'Pending']}`}>
                                            {ret.inspection_status || 'Pending'}
                                        </span>
                                    </td>
                                    <td>{ret.requested_at ? new Date(ret.requested_at).toLocaleDateString() : '-'}</td>
                                    <td>{ret.received_at ? new Date(ret.received_at).toLocaleDateString() : '-'}</td>
                                    <td>
                                        {ret.return_status === 'Received' && !ret.inspection_status && (
                                            <button 
                                                className={styles.inspectBtn}
                                                onClick={() => setInspectingReturn(ret)}
                                            >
                                                Inspect
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {inspectingReturn && (
                <div className={styles.modalOverlay}>
                    <div className={styles.modal}>
                        <h3>Inspect Return</h3>
                        <div className={styles.modalBody}>
                            <p><strong>SKU:</strong> {inspectingReturn.sku}</p>
                            <p><strong>Product:</strong> {inspectingReturn.product_name}</p>
                            <p><strong>Quantity:</strong> {inspectingReturn.quantity}</p>
                            <p><strong>Return Reason:</strong> {inspectingReturn.return_reason}</p>
                            
                            <form onSubmit={handleInspectSubmit} className={styles.inspectForm}>
                                <div className={styles.formGroup}>
                                    <label>Decision:</label>
                                    <div className={styles.radioGroup}>
                                        <label>
                                            <input 
                                                type="radio" 
                                                name="decision"
                                                value="RESTOCK"
                                                checked={inspectionDecision === 'RESTOCK'}
                                                onChange={(e) => setInspectionDecision(e.target.value)}
                                            />
                                            Good Condition (Restock)
                                        </label>
                                        <label>
                                            <input 
                                                type="radio" 
                                                name="decision"
                                                value="DEFECTIVE"
                                                checked={inspectionDecision === 'DEFECTIVE'}
                                                onChange={(e) => setInspectionDecision(e.target.value)}
                                            />
                                            Defective
                                        </label>
                                    </div>
                                </div>
                                <div className={styles.formGroup}>
                                    <label>Inspection Notes:</label>
                                    <textarea 
                                        value={inspectionNotes}
                                        onChange={(e) => setInspectionNotes(e.target.value)}
                                        placeholder="Add remarks..."
                                        rows="3"
                                        className={styles.textarea}
                                    />
                                </div>
                                <div className={styles.modalActions}>
                                    <button 
                                        type="button" 
                                        className={styles.cancelBtn}
                                        onClick={() => setInspectingReturn(null)}
                                        disabled={inspectMutation.isLoading}
                                    >
                                        Cancel
                                    </button>
                                    <button 
                                        type="submit" 
                                        className={styles.submitBtn}
                                        disabled={inspectMutation.isLoading}
                                    >
                                        {inspectMutation.isLoading ? 'Saving...' : 'Submit'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AmazonReturns;

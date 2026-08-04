import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import styles from './DefectiveInventory.module.css';

const DefectiveInventory = () => {
    const [statusFilter, setStatusFilter] = useState('');
    const [search, setSearch] = useState('');

    const { data: defectives = [], isLoading } = useQuery({
        queryKey: ['defectiveInventory', statusFilter, search],
        queryFn: async () => {
            const params = {};
            if (statusFilter) params.status = statusFilter;
            if (search) params.sku = search;
            const res = await api.get('/api/defective-inventory/', { params });
            return res.data;
        }
    });

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div>
                    <h2>Defective Inventory</h2>
                    <p className={styles.subtitle}>Manage unsellable products from returns and inspections.</p>
                </div>
            </div>

            <div className={styles.filters}>
                <input 
                    type="text" 
                    placeholder="Search SKU..." 
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
                    <option value="NEW">New</option>
                    <option value="UNDER_REVIEW">Under Review</option>
                    <option value="REPAIR">Repair</option>
                    <option value="RETURN_VENDOR">Return to Vendor</option>
                    <option value="SCRAPPED">Scrapped</option>
                    <option value="DISPOSED">Disposed</option>
                </select>
            </div>

            <div className={styles.tableContainer}>
                {isLoading ? (
                    <div className={styles.loading}>Loading defective inventory...</div>
                ) : defectives.length === 0 ? (
                    <div className={styles.empty}>No defective items found.</div>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>SKU</th>
                                <th>Product</th>
                                <th>Return ID</th>
                                <th>Quantity</th>
                                <th>Return Reason</th>
                                <th>Remarks</th>
                                <th>Current Status</th>
                                <th>Inspection Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {defectives.map(item => (
                                <tr key={item.id}>
                                    <td>{item.sku_snapshot}</td>
                                    <td>{item.product_name_snapshot}</td>
                                    <td>{item.amazon_return_id}</td>
                                    <td>{item.quantity}</td>
                                    <td>{item.return_reason}</td>
                                    <td>{item.inspection_notes || '-'}</td>
                                    <td>
                                        <span className={`${styles.badge} ${styles[item.status]}`}>
                                            {item.status.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td>{item.inspection_date ? new Date(item.inspection_date).toLocaleDateString() : '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default DefectiveInventory;

import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { PurchaseService } from '../../services/purchaseService';
import { DataTable } from '../../components/DataTable/DataTable';

export default function PurchasesList() {
  const { user } = useAuthStore();
  const [payables, setPayables] = useState([]);

  useEffect(() => {
    if (user?.company_id) {
      PurchaseService.getPayables(user.company_id)
        .then(setPayables)
        .catch(e => console.error("Failed to load payables", e));
    }
  }, [user]);

  const columns = [
    { name: 'ID', selector: row => row.id, sortable: true },
    { name: 'Vendor Name', selector: row => row.name, sortable: true },
    { name: 'Total Payable Balance (₹)', selector: row => row.payable_balance.toFixed(2), sortable: true },
  ];

  return (
    <div style={{ padding: '20px' }}>
      <h2>Vendor Payables & Purchases</h2>
      <p>Total outstanding amounts to vendors based on Received Purchases.</p>
      
      <div style={{ marginTop: '20px' }}>
        <DataTable
          title="Vendor Balances"
          columns={columns}
          data={payables}
          pagination
        />
      </div>
    </div>
  );
}

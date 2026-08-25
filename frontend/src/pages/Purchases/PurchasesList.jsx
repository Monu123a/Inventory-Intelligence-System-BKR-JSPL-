import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import useCompanyStore from '../../stores/useCompanyStore';
import { PurchaseService } from '../../services/purchaseService';
import { DataTable } from '../../components/DataTable/DataTable';

export default function PurchasesList() {
  const { user } = useAuthStore();
  const { currentCompany } = useCompanyStore();
  const activeCompanyId = currentCompany?.id || 2;
  const [payables, setPayables] = useState([]);

  useEffect(() => {
    if (activeCompanyId) {
      PurchaseService.getPayables(activeCompanyId)
        .then(setPayables)
        .catch(e => console.error("Failed to load payables", e));
    }
  }, [user]);

  const columns = [
    { name: 'ID', key: 'id' },
    { name: 'Vendor Name', key: 'name' },
    { name: 'Total Payable Balance (₹)', key: 'payable_balance', render: (_, row) => Number(row.payable_balance || 0).toFixed(2) },
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

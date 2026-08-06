import React, { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card } from '../../components/Card/Card';
import styles from './Reports.module.css';

// Import the new modular views
import { SalesReport } from './views/SalesReport';
import { InventoryReport } from './views/InventoryReport';
import { DispatchReport } from './views/DispatchReport';
import { FCReturnReport } from './views/FCReturnReport';
import { DefectiveReport } from './views/DefectiveReport';

const Reports = () => {
  const [activeTab, setActiveTab] = useState('sales');

  const tabs = [
    { id: 'sales', label: 'Sales Report' },
    { id: 'inventory', label: 'Inventory Status' },
    { id: 'dispatches', label: 'Dispatch Report' },
    { id: 'returns', label: 'Amazon Returns' },
    { id: 'defective', label: 'Defective Inventory' },
  ];

  return (
    <PageContainer title="Operational Reports">
      <Card noPadding>
        {/* Tab Navigation */}
        <div className={styles.tabHeader}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`${styles.tabBtn} ${activeTab === tab.id ? styles.activeTab : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        
        {/* View Container */}
        <div className={styles.reportContainer}>
          {activeTab === 'sales' && <SalesReport />}
          {activeTab === 'inventory' && <InventoryReport />}
          {activeTab === 'dispatches' && <DispatchReport />}
          {activeTab === 'returns' && <FCReturnReport />}
          {activeTab === 'defective' && <DefectiveReport />}
        </div>
      </Card>
    </PageContainer>
  );
};

export default Reports;

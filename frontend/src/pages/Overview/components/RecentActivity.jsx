import React from 'react';
import { Card } from '../../../components/Card/Card';
import { DataTable, TableHeader, TableRow } from '../../../components/DataTable';
import { StatusBadge } from '../../../components/StatusBadge/StatusBadge';

export const RecentActivity = ({ activities }) => {
  const columns = [
    {
      key: 'timestamp',
      label: 'Time',
      render: (val) => new Date(val).toLocaleString()
    },
    {
      key: 'type',
      label: 'Type'
    },
    {
      key: 'description',
      label: 'Description'
    },
    {
      key: 'status',
      label: 'Status',
      render: (val) => <StatusBadge status={val} />
    }
  ];

  return (
    <Card title="Recent Activity">
      {(!activities || activities.length === 0) ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          No recent activity found.
        </div>
      ) : (
        <DataTable>
          <TableHeader columns={columns} />
          <tbody>
            {activities.map(activity => (
              <TableRow key={activity.id} row={activity} columns={columns} />
            ))}
          </tbody>
        </DataTable>
      )}
    </Card>
  );
};

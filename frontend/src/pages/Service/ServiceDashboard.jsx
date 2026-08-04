import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import useCompanyStore from '../../stores/useCompanyStore';

export default function ServiceDashboard() {
  const navigate = useNavigate();
  const currentCompany = useCompanyStore(state => state.currentCompany);
  
  const [stats, setStats] = useState({
    pending: 0,
    completed: 0,
    replacements: 0,
    upcomingReminders: 0
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      if (!currentCompany?.id) return;
      try {
        setLoading(true);
        const [activeRes, historyRes, remindersRes] = await Promise.all([
          api.get('/api/services?status=active'),
          api.get('/api/services?status=history'),
          api.get('/api/service-reminders')
        ]);
        
        const activeServices = activeRes.data?.items || activeRes.data || [];
        const historyServices = historyRes.data?.items || historyRes.data || [];
        const reminders = remindersRes.data?.items || remindersRes.data || [];

        const pending = activeServices.filter(s => s.status === 'Pending').length;
        const completed = historyServices.filter(s => s.status === 'Completed').length;
        
        let replacements = 0;
        [...activeServices, ...historyServices].forEach(s => {
          if (s.items) {
             replacements += s.items.filter(i => i.is_replacement || i.replacement_item_id).length;
          }
        });

        const upcomingReminders = reminders.filter(r => r.status === 'Pending').length;

        setStats({ pending, completed, replacements, upcomingReminders });
      } catch (err) {
        console.error('Error fetching service dashboard data', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [currentCompany]);

  const cardStyle = {
    padding: '24px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    flex: '1',
    minWidth: '200px',
    border: '1px solid #eaeaea',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    cursor: 'pointer'
  };

  const statNumberStyle = {
    fontSize: '32px',
    fontWeight: '700',
    color: '#2563eb',
    marginTop: '12px'
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Service Dashboard</h2>
        <button 
          onClick={() => navigate('/service/create')}
          style={{ padding: '10px 20px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500' }}
        >
          + New Service Record
        </button>
      </div>

      {loading ? (
        <p>Loading Dashboard...</p>
      ) : (
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <div style={cardStyle} onClick={() => navigate('/service/records')}>
            <h3 style={{ margin: 0, color: '#4b5563', fontSize: '16px' }}>Active / Pending</h3>
            <div style={statNumberStyle}>{stats.pending}</div>
          </div>
          
          <div style={cardStyle} onClick={() => navigate('/service/history')}>
            <h3 style={{ margin: 0, color: '#4b5563', fontSize: '16px' }}>Completed Services</h3>
            <div style={statNumberStyle}>{stats.completed}</div>
          </div>
          
          <div style={cardStyle} onClick={() => navigate('/service/reminders')}>
            <h3 style={{ margin: 0, color: '#4b5563', fontSize: '16px' }}>Upcoming Reminders</h3>
            <div style={statNumberStyle}>{stats.upcomingReminders}</div>
          </div>
        </div>
      )}
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import ApprovalModal from './ApprovalModal';
import { FiLock, FiCheckCircle } from 'react-icons/fi';
import styles from './Approvals.module.css';

const ApprovalDashboard = () => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedReqId, setSelectedReqId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("PENDING");

  // Gatekeeper state
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const loadRequests = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/api/admin-approvals?status=${statusFilter}`);
      setRequests(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isUnlocked) {
      loadRequests();
    }
  }, [statusFilter, isUnlocked]);

  const handleUnlock = async (e) => {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      await api.post('/api/admin-approvals/verify-password', { password: authPassword });
      setIsUnlocked(true);
    } catch (err) {
      setAuthError("Invalid admin password");
    } finally {
      setAuthLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const cls = status === 'PENDING' ? styles.badgePending
      : status === 'EXECUTED' ? styles.badgeExecuted
      : status === 'FAILED' ? styles.badgeFailed
      : styles.badgeDefault;
    return <span className={`${styles.badge} ${cls}`}>{status}</span>;
  };

  if (!isUnlocked) {
    return (
      <div className={styles.lockScreen}>
        <form onSubmit={handleUnlock} className={styles.lockCard}>
          <div className={styles.lockIcon}>
            <FiLock size={48} />
          </div>
          <h2 className={styles.lockTitle}>Admin Approvals</h2>
          <p className={styles.lockDescription}>
            Please enter your admin password to view and manage pending approvals. Once unlocked, you will not be asked again during this session.
          </p>
          
          {authError && <div className={styles.lockError}>{authError}</div>}
          
          <input
            type="password"
            autoFocus
            className={styles.lockInput}
            placeholder="Admin Password"
            value={authPassword}
            onChange={e => setAuthPassword(e.target.value)}
          />
          <button
            type="submit"
            disabled={authLoading || !authPassword}
            className={styles.lockBtn}
          >
            {authLoading ? 'Verifying...' : 'Unlock Approvals'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <h1 className={styles.pageTitle}>
          <FiCheckCircle color="var(--color-success)" size={20} /> Admin Approvals
        </h1>
        <select 
          value={statusFilter} 
          onChange={e => setStatusFilter(e.target.value)}
          className={styles.select}
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="EXECUTED">Executed</option>
          <option value="REJECTED">Rejected</option>
          <option value="CANCELED">Canceled</option>
          <option value="EXPIRED">Expired</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {loading ? (
        <p style={{ padding: 'var(--spacing-6)', color: 'var(--color-text-muted)' }}>Loading...</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Requested By</th>
                <th>Date</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(req => (
                <tr key={req.id}>
                  <td>{req.id}</td>
                  <td className={styles.typeBold}>{req.request_type}</td>
                  <td>{req.requested_by}</td>
                  <td>{new Date(req.created_at).toLocaleString()}</td>
                  <td>{getStatusBadge(req.status)}</td>
                  <td>
                    <button 
                      onClick={() => setSelectedReqId(req.id)}
                      className={styles.reviewBtn}
                    >
                      {req.status === 'PENDING' ? 'Review & Approve' : 'View Details'}
                    </button>
                  </td>
                </tr>
              ))}
              {requests.length === 0 && (
                <tr><td colSpan="6" className={styles.emptyRow}>No requests found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <ApprovalModal 
        show={!!selectedReqId}
        requestId={selectedReqId}
        onHide={() => setSelectedReqId(null)}
        onActionComplete={loadRequests}
      />
    </div>
  );
};

export default ApprovalDashboard;

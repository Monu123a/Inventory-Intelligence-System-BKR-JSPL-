import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import ApprovalModal from './ApprovalModal';
import { FiLock } from 'react-icons/fi';

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

  if (!isUnlocked) {
    return (
      <div className="flex items-center justify-center min-h-[80vh] p-6">
        <form onSubmit={handleUnlock} className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <div className="flex justify-center mb-4 text-indigo-600">
            <FiLock size={48} />
          </div>
          <h2 className="text-2xl font-bold text-center mb-6">Admin Approvals</h2>
          <p className="text-sm text-gray-600 text-center mb-6">
            Please enter your admin password to view and manage pending approvals. Once unlocked, you will not be asked again during this session.
          </p>
          
          {authError && <div className="bg-red-100 text-red-700 p-2 text-sm rounded mb-4 text-center">{authError}</div>}
          
          <input
            type="password"
            autoFocus
            className="w-full border rounded p-3 mb-4 focus:ring focus:ring-indigo-200"
            placeholder="Admin Password"
            value={authPassword}
            onChange={e => setAuthPassword(e.target.value)}
          />
          <button
            type="submit"
            disabled={authLoading || !authPassword}
            className="w-full bg-indigo-600 text-white font-semibold py-3 rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {authLoading ? 'Verifying...' : 'Unlock Approvals'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FiLock className="text-green-500" size={20} /> Admin Approvals
        </h1>
        <select 
          value={statusFilter} 
          onChange={e => setStatusFilter(e.target.value)}
          className="border rounded p-2"
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
        <p>Loading...</p>
      ) : (
        <div className="bg-white rounded shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requested By</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {requests.map(req => (
                <tr key={req.id}>
                  <td className="px-6 py-4 text-sm">{req.id}</td>
                  <td className="px-6 py-4 text-sm font-semibold">{req.request_type}</td>
                  <td className="px-6 py-4 text-sm">{req.requested_by}</td>
                  <td className="px-6 py-4 text-sm">{new Date(req.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${
                      req.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                      req.status === 'EXECUTED' ? 'bg-green-100 text-green-800' :
                      req.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {req.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <button 
                      onClick={() => setSelectedReqId(req.id)}
                      className="text-indigo-600 hover:text-indigo-900 font-medium"
                    >
                      {req.status === 'PENDING' ? 'Review & Approve' : 'View Details'}
                    </button>
                  </td>
                </tr>
              ))}
              {requests.length === 0 && (
                <tr><td colSpan="6" className="px-6 py-4 text-center text-gray-500">No requests found.</td></tr>
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

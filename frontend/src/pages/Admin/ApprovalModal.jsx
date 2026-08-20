import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getAuthHeaders } from '../../utils/auth';

const ApprovalModal = ({ show, onHide, requestId, onActionComplete }) => {
  const [preview, setPreview] = useState(null);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (show && requestId) {
      loadPreview();
    }
  }, [show, requestId]);

  const loadPreview = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`http://localhost:8000/api/admin-approvals/${requestId}/preview`, {
        headers: getAuthHeaders()
      });
      setPreview(res.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load preview");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    try {
      setLoading(true);
      await axios.post(`http://localhost:8000/api/admin-approvals/${requestId}/approve`, {
        idempotency_key: `ui-exec-${Date.now()}`,
        comment: comment
      }, { headers: getAuthHeaders() });
      onActionComplete();
      onHide();
    } catch (err) {
      setError(err.response?.data?.detail?.reason === "snapshot_mismatch" 
        ? "Data changed since request. " + JSON.stringify(err.response.data.detail.diff)
        : err.response?.data?.detail || "Approval failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    try {
      setLoading(true);
      await axios.post(`http://localhost:8000/api/admin-approvals/${requestId}/cancel`, {}, { headers: getAuthHeaders() });
      onActionComplete();
      onHide();
    } catch (err) {
      setError("Rejection failed");
    } finally {
      setLoading(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg w-3/4 max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">Review Request #{requestId}</h2>
        
        {error && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">{error}</div>}
        
        {loading ? (
          <div>Loading preview...</div>
        ) : preview ? (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Impact Preview</h3>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
              {JSON.stringify(preview.preview, null, 2)}
            </pre>
            
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold text-sm">Original State (When Requested)</h4>
                <pre className="text-xs bg-gray-50 p-2 border">{JSON.stringify(preview.original_snapshot, null, 2)}</pre>
              </div>
              <div>
                <h4 className="font-semibold text-sm">Current State (Live DB)</h4>
                <pre className="text-xs bg-gray-50 p-2 border">{JSON.stringify(preview.current_snapshot, null, 2)}</pre>
              </div>
            </div>
          </div>
        ) : null}

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">Admin Comment (Optional)</label>
          <textarea 
            className="w-full mt-1 border rounded p-2" 
            rows="2"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>

        <div className="flex justify-end gap-2">
          <button onClick={onHide} className="px-4 py-2 border rounded">Close</button>
          <button onClick={handleReject} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50" disabled={loading}>Reject</button>
          <button onClick={handleApprove} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50" disabled={loading || error}>Approve & Execute</button>
        </div>
      </div>
    </div>
  );
};

export default ApprovalModal;

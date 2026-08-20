import React, { useState } from 'react';
import { useApprovalStore } from '../../stores/useApprovalStore';
import api from '../../services/api';
import { useNotificationStore } from '../../stores/notificationStore';
import { FiAlertCircle, FiX } from 'react-icons/fi';

export default function OperatorApprovalModal() {
  const { isOpen, requestType, payload, closeModal } = useApprovalStore();
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const addNotification = useNotificationStore(state => state.addNotification);

  if (!isOpen) return null;

  const createRequest = async () => {
    setLoading(true);
    const idempotencyKey = crypto.randomUUID();
    
    try {
      const res = await api.post('/api/admin-approvals/', {
        request_type: requestType,
        payload,
        idempotency_key: idempotencyKey,
        company_id: payload.company_id,
        related_entity: payload.product_id || payload.id || null
      });
      
      addNotification({
        type: 'success',
        title: 'Request Created',
        message: `Your escalation request has been submitted to Admins. (ID: ${res.data.request_id})`
      });
      closeModal();
    } catch (err) {
      // Error handled by generic interceptor usually
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-lg relative">
        <button 
          onClick={closeModal} 
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
        >
          <FiX size={24} />
        </button>
        
        <div className="flex items-center gap-3 mb-4 text-amber-600">
          <FiAlertCircle size={24} />
          <h3 className="text-xl font-bold text-gray-900">Admin Approval Required</h3>
        </div>
        
        <p className="text-sm text-gray-600 mb-4">
          You do not have direct permission to perform this action. You can submit this change as a request for an Admin to review and execute.
        </p>

        <div className="mb-4">
          <span className="text-xs font-semibold text-gray-500 uppercase">Operation Type</span>
          <div className="font-mono text-sm bg-gray-50 p-2 rounded border border-gray-200 mt-1">
            {requestType}
          </div>
        </div>

        <div className="mb-4">
          <span className="text-xs font-semibold text-gray-500 uppercase">Payload (Changes)</span>
          <pre className="text-xs font-mono bg-gray-50 p-3 rounded border border-gray-200 mt-1 max-h-40 overflow-y-auto">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>

        <div className="mb-6">
          <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
            Reason / Justification (Optional)
          </label>
          <textarea 
            className="w-full border border-gray-300 rounded p-2 text-sm focus:ring-indigo-500 focus:border-indigo-500" 
            rows="3"
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="Explain why this change is needed..."
          />
        </div>

        <div className="flex justify-end gap-3">
          <button 
            onClick={closeModal}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 font-medium"
            disabled={loading}
          >
            Cancel
          </button>
          <button 
            onClick={createRequest} 
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 font-medium flex items-center justify-center min-w-[140px]"
          >
            {loading ? 'Submitting...' : 'Request Approval'}
          </button>
        </div>
      </div>
    </div>
  );
}

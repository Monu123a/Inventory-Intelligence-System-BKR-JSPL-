import React, { useState } from 'react';
import { useApprovalStore } from '../../stores/useApprovalStore';
import api from '../../services/api';
import { useNotificationStore } from '../../stores/notificationStore';
import { FiSend, FiX, FiAlertCircle } from 'react-icons/fi';

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
      setComment('');
      closeModal();
    } catch (err) {
      // Error handled by generic interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={headerStyle}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
            <FiAlertCircle color="#d97706" /> Admin Approval Required
          </h3>
          <button type="button" onClick={closeModal} style={closeBtnStyle}>
            <FiX size={20} />
          </button>
        </div>

        <div style={bodyStyle}>
          <p style={{ margin: '0 0 16px', fontSize: '14px', color: '#475569' }}>
            You do not have direct permission to perform this action. Submit this change as a request for an Admin to review and execute.
          </p>

          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Operation Type</label>
            <div style={codeBoxStyle}>{requestType}</div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Payload (Changes)</label>
            <pre style={preStyle}>
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={labelStyle}>Reason / Justification (Optional)</label>
            <textarea
              style={textareaStyle}
              rows="3"
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="Explain why this change is needed..."
            />
          </div>
        </div>

        <div style={footerStyle}>
          <button type="button" onClick={closeModal} style={cancelBtnStyle} disabled={loading}>
            Cancel
          </button>
          <button onClick={createRequest} disabled={loading} style={submitBtnStyle}>
            <FiSend size={14} style={{ marginRight: '6px' }} />
            {loading ? 'Submitting...' : 'Request Approval'}
          </button>
        </div>
      </div>
    </div>
  );
}

const overlayStyle = {
  position: 'fixed',
  top: 0, left: 0, right: 0, bottom: 0,
  backgroundColor: 'rgba(15, 23, 42, 0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 9999,
  padding: '16px'
};

const modalStyle = {
  backgroundColor: '#ffffff',
  borderRadius: '8px',
  width: '100%',
  maxWidth: '500px',
  maxHeight: '90vh',
  overflowY: 'auto',
  boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
  overflow: 'hidden'
};

const headerStyle = {
  padding: '16px 24px',
  borderBottom: '1px solid #e2e8f0',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  backgroundColor: '#fffbeb'
};

const closeBtnStyle = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  color: '#9ca3af',
  padding: '4px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const bodyStyle = {
  padding: '24px'
};

const labelStyle = {
  fontSize: '12px',
  fontWeight: '600',
  color: '#64748b',
  textTransform: 'uppercase',
  marginBottom: '4px',
  display: 'block'
};

const codeBoxStyle = {
  fontFamily: 'monospace',
  fontSize: '13px',
  backgroundColor: '#f8fafc',
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #e2e8f0',
  marginTop: '4px',
  color: '#0f172a'
};

const preStyle = {
  fontFamily: 'monospace',
  fontSize: '12px',
  backgroundColor: '#f8fafc',
  padding: '12px',
  borderRadius: '4px',
  border: '1px solid #e2e8f0',
  marginTop: '4px',
  maxHeight: '160px',
  overflowY: 'auto',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  margin: '4px 0 0 0'
};

const textareaStyle = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #cbd5e1',
  fontSize: '14px',
  boxSizing: 'border-box',
  fontFamily: 'inherit',
  resize: 'vertical'
};

const footerStyle = {
  padding: '16px 24px',
  borderTop: '1px solid #e2e8f0',
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '12px',
  backgroundColor: '#f8fafc'
};

const cancelBtnStyle = {
  padding: '8px 16px',
  borderRadius: '4px',
  border: '1px solid #e2e8f0',
  background: '#ffffff',
  color: '#0f172a',
  fontWeight: '500',
  cursor: 'pointer',
  fontSize: '14px'
};

const submitBtnStyle = {
  padding: '8px 16px',
  borderRadius: '4px',
  border: 'none',
  background: '#d97706',
  color: '#ffffff',
  fontWeight: '500',
  cursor: 'pointer',
  fontSize: '14px',
  display: 'flex',
  alignItems: 'center'
};

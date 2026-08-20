import React, { useState } from 'react';
import { FiLock, FiX, FiSend } from 'react-icons/fi';
import { useAuthStore } from '../../stores/authStore';

const AdminPasswordModal = ({ isOpen, onClose, onSubmit, actionName }) => {
  const [password, setPassword] = useState('');
  const user = useAuthStore(state => state.user);

  // Only show "Request Approval" for non-Admin users
  const isAdmin = user?.role === 'Admin';

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!password) return;
    onSubmit(password);
    setPassword('');
  };

  const handleRequestApproval = () => {
    onSubmit("REQUEST_APPROVAL");
    setPassword('');
  };

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={headerStyle}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FiLock /> Admin Verification
          </h3>
          <button type="button" onClick={onClose} style={closeBtnStyle}>
            <FiX size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div style={bodyStyle}>
            <p style={{ margin: '0 0 16px', fontSize: '14px', color: '#475569' }}>
              Please enter your admin password to {actionName}.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', fontWeight: '600', color: '#0f172a', textTransform: 'uppercase' }}>
                Admin Password
              </label>
              <input
                type="password"
                autoFocus
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                style={inputStyle}
                placeholder="Enter password..."
              />
            </div>
          </div>
          <div style={footerStyle}>
            <button type="button" onClick={onClose} style={cancelBtnStyle}>
              Cancel
            </button>
            <div style={{ display: 'flex', gap: '8px' }}>
              {!isAdmin && (
                <button type="button" onClick={handleRequestApproval} style={requestApprovalBtnStyle}>
                  <FiSend size={14} style={{ marginRight: '4px' }} />
                  Request Approval
                </button>
              )}
              <button type="submit" style={submitBtnStyle}>
                Verify & Proceed
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AdminPasswordModal;

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
  maxWidth: '450px',
  boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
  overflow: 'hidden'
};

const headerStyle = {
  padding: '16px 24px',
  borderBottom: '1px solid #e2e8f0',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  backgroundColor: '#f8fafc'
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

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #cbd5e1',
  fontSize: '14px',
  boxSizing: 'border-box'
};

const footerStyle = {
  padding: '16px 24px',
  borderTop: '1px solid #e2e8f0',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
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

const requestApprovalBtnStyle = {
  padding: '8px 16px',
  borderRadius: '4px',
  border: '1px solid #f59e0b',
  background: '#fffbeb',
  color: '#d97706',
  fontWeight: '500',
  cursor: 'pointer',
  fontSize: '14px',
  display: 'flex',
  alignItems: 'center'
};

const submitBtnStyle = {
  padding: '8px 16px',
  borderRadius: '4px',
  border: 'none',
  background: '#2563eb',
  color: '#ffffff',
  fontWeight: '500',
  cursor: 'pointer',
  fontSize: '14px'
};

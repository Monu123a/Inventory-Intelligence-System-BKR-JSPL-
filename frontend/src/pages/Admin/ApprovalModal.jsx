import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { FiX } from 'react-icons/fi';
import styles from './Approvals.module.css';

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
      const res = await api.get(`/api/admin-approvals/${requestId}/preview`);
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
      await api.post(`/api/admin-approvals/${requestId}/approve`, {
        idempotency_key: `ui-exec-${Date.now()}`,
        comment: comment
      });
      onActionComplete();
      onHide();
    } catch (err) {
      setError(err.response?.data?.detail?.reason === "snapshot_mismatch" 
        ? "⚠️ Data has changed since this request was created. Diff: " + JSON.stringify(err.response.data.detail.diff)
        : err.response?.data?.detail || "Approval failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    try {
      setLoading(true);
      await api.post(`/api/admin-approvals/${requestId}/cancel`, {});
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
    <div className={styles.modalOverlay}>
      <div className={styles.modalCard}>
        <div className={styles.modalHeader}>
          <h3 className={styles.modalTitle}>Review Request #{requestId}</h3>
          <button onClick={onHide} className={styles.closeBtn}>
            <FiX size={20} />
          </button>
        </div>

        <div className={styles.modalBody}>
          {error && <div className={styles.errorBox}>{error}</div>}

          {loading ? (
            <p style={{ color: 'var(--color-text-muted)' }}>Loading preview...</p>
          ) : preview ? (
            <>
              {preview.request_reason && (
                <div style={{ marginBottom: 'var(--spacing-4)' }}>
                  <h4 className={styles.sectionTitle}>Requester Reason</h4>
                  <div style={{ padding: '12px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #e2e8f0', color: '#334155' }}>
                    {preview.request_reason}
                  </div>
                </div>
              )}

              <div style={{ marginBottom: 'var(--spacing-4)' }}>
                <h4 className={styles.sectionTitle}>Impact Preview</h4>
                <pre className={styles.preBlock}>
                  {JSON.stringify(preview.preview, null, 2)}
                </pre>
              </div>

              <div className={styles.snapshotGrid}>
                <div>
                  <span className={styles.sectionLabel}>Original State (When Requested)</span>
                  <pre className={styles.preBlock}>
                    {JSON.stringify(preview.original_snapshot, null, 2)}
                  </pre>
                </div>
                <div>
                  <span className={styles.sectionLabel}>Current State (Live DB)</span>
                  <pre className={styles.preBlock}>
                    {JSON.stringify(preview.current_snapshot, null, 2)}
                  </pre>
                </div>
              </div>
            </>
          ) : null}

          {preview?.status === 'PENDING' && (
            <div style={{ marginTop: 'var(--spacing-4)' }}>
              <label className={styles.sectionLabel}>Admin Comment (Optional)</label>
              <textarea 
                className={styles.commentArea}
                rows="2"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a note..."
              />
            </div>
          )}
        </div>

        <div className={styles.modalFooter}>
          <button onClick={onHide} className={styles.btnCancel}>Close</button>
          {preview?.status === 'PENDING' && (
            <>
              <button onClick={handleReject} className={styles.btnReject} disabled={loading}>Reject</button>
              <button onClick={handleApprove} className={styles.btnApprove} disabled={loading || error}>Approve & Execute</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ApprovalModal;

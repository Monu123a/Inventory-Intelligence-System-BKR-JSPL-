import React, { useState } from 'react';
import Modal from '../../../components/common/Modal';
import Button from '../../../components/common/Button';
import styles from './UploadModal.module.css';
import api from '../../../services/api';
import { useNotifications } from '../../../contexts/NotificationContext';
import { useNavigate } from 'react-router-dom';

const TallyUploadModal = ({ isOpen, onClose }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [previewItems, setPreviewItems] = useState(null);
  const { addNotification } = useNotifications();
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setPreviewItems(null);
    }
  };

  const handlePreview = async () => {
    if (!file) {
      addNotification({ type: 'error', message: 'Please select a file first' });
      return;
    }
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/api/bulk-upload/tally-bill-preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setPreviewItems(res.data.items);
      addNotification({ type: 'success', message: 'Tally bill parsed successfully!' });
    } catch (err) {
      addNotification({ type: 'error', message: err.response?.data?.detail || 'Failed to parse Tally bill' });
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreviewItems(null);
    const el = document.getElementById('tally-file-upload');
    if (el) el.value = '';
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };
  
  const handleProceed = () => {
    // In a real flow, we could save this to localStorage and redirect to POS
    // Or we could create a draft offline_sale and sync it.
    // Let's pass it via state to POS if they click proceed
    addNotification({ type: 'success', message: 'Ready for POS integration!' });
    navigate('/pos', { state: { tallyItems: previewItems } });
    handleClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Upload Tally Bill" maxWidth="900px">
      <div className={styles.uploadContainer}>
        {!previewItems ? (
          <div className={styles.dropZone}>
            <input 
              type="file" 
              id="tally-file-upload"
              accept=".xlsx,.xls" 
              onChange={handleFileChange}
              className={styles.fileInput}
              style={{ display: 'none' }}
            />
            <label htmlFor="tally-file-upload" style={{ cursor: 'pointer', padding: '40px', border: '2px dashed #cbd5e1', display: 'block', textAlign: 'center', borderRadius: '8px' }}>
              <div style={{ fontSize: '3rem', marginBottom: '10px' }}>📑</div>
              <div style={{ fontWeight: '500', color: '#475569' }}>
                {file ? file.name : "Click to select Tally .xlsx file"}
              </div>
            </label>
            <div style={{ marginTop: '20px', textAlign: 'center' }}>
              <Button onClick={handlePreview} disabled={!file || uploading}>
                {uploading ? 'Parsing...' : 'Preview Items'}
              </Button>
            </div>
          </div>
        ) : (
          <div className={styles.previewSection}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
              <h4 style={{ margin: 0 }}>Parsed Items ({previewItems.length})</h4>
              <Button variant="secondary" onClick={handleReset}>Upload Different File</Button>
            </div>
            
            <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '4px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: '#f8fafc', zIndex: 1 }}>
                  <tr style={{ borderBottom: '2px solid #e2e8f0', textAlign: 'left' }}>
                    <th style={{ padding: '10px' }}>Sl</th>
                    <th style={{ padding: '10px' }}>Description</th>
                    <th style={{ padding: '10px' }}>Matched SKU</th>
                    <th style={{ padding: '10px' }}>Qty</th>
                    <th style={{ padding: '10px' }}>Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {previewItems.map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '10px' }}>{item.sl_no}</td>
                      <td style={{ padding: '10px' }}>{item.description}</td>
                      <td style={{ padding: '10px', color: item.matched_sku ? '#059669' : '#dc2626', fontWeight: 'bold' }}>
                        {item.matched_sku || 'Unmatched'}
                      </td>
                      <td style={{ padding: '10px' }}>{item.quantity}</td>
                      <td style={{ padding: '10px' }}>{item.rate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {previewItems.some(i => !i.matched_sku) && (
              <div style={{ color: '#b91c1c', marginTop: '15px', padding: '10px', backgroundColor: '#fee2e2', borderRadius: '4px', fontSize: '0.9rem' }}>
                <strong>Warning:</strong> Some items could not be automatically matched to an existing SKU. You will need to map them manually in the POS.
              </div>
            )}
            
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <Button variant="secondary" onClick={handleClose}>Cancel</Button>
              <Button variant="primary" onClick={handleProceed}>
                Proceed to Checkout
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default TallyUploadModal;

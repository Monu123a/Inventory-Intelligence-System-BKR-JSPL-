import React, { useState } from 'react';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import styles from './UploadModal.module.css';
import api from '../../../services/api';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

const TallyUploadModal = ({ isOpen, onClose, warehouses }) => {
  const [warehouseId, setWarehouseId] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [previewItems, setPreviewItems] = useState(null);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setPreviewItems(null);
    }
  };

  const handlePreview = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/api/bulk-upload/tally-bill-preview', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setPreviewItems(res.data.items);
      toast.success('Tally bill parsed successfully!');
    } catch (err) {
      
    let errMsg = 'An error occurred';
    if (err.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        errMsg = err.response.data.detail;
      } else if (Array.isArray(err.response.data.detail)) {
        errMsg = err.response.data.detail[0]?.msg || 'Validation Error';
      }
    } else if (err.message) {
      errMsg = err.message;
    }
    toast.error(errMsg);
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
  
  const handleProceed = async () => {
    if (!warehouseId) {
      toast.error('Please select a destination warehouse');
      return;
    }
    
    // Only upload the items that actually mapped to an SKU
    const validItems = previewItems.filter(i => i.matched_sku);
    if (validItems.length === 0) {
      toast.error('No valid items to upload');
      return;
    }
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('warehouse_id', warehouseId);
    formData.append('items', JSON.stringify(validItems));
    
    try {
      await api.post('/api/bulk-upload/tally-bill-confirm', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Inventory updated successfully!');
      setTimeout(() => {
        window.location.reload();
      }, 1500);
      handleClose();
    } catch (err) {
      
    let errMsg = 'An error occurred';
    if (err.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        errMsg = err.response.data.detail;
      } else if (Array.isArray(err.response.data.detail)) {
        errMsg = err.response.data.detail[0]?.msg || 'Validation Error';
      }
    } else if (err.message) {
      errMsg = err.message;
    }
    toast.error(errMsg);
      setUploading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Upload Tally Bill" maxWidth="900px">
      <div className={styles.uploadContainer}>
        {!previewItems ? (
          <div className={styles.dropZone}>
            <div style={{ marginBottom: '20px', textAlign: 'left' }}>
              <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>Destination Warehouse</label>
              <select 
                value={warehouseId} 
                onChange={e => setWarehouseId(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
              >
                <option value="">-- Select Warehouse --</option>
                {warehouses.map(wh => (
                  <option key={wh.id} value={wh.id}>{wh.name}</option>
                ))}
              </select>
            </div>
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
                Update Inventory
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default TallyUploadModal;

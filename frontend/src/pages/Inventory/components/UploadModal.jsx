import React, { useState } from 'react';
import { Modal } from '../../../components/Modal/Modal';
import { ConfirmationDialog } from '../../../components/Modal/ConfirmationDialog';
import Button from '../../../components/forms/Button';
import { useUploadInventory } from '../../../hooks/useInventory';
import AdminPasswordModal from '../../../components/common/AdminPasswordModal';
import { FiUploadCloud, FiAlertCircle } from 'react-icons/fi';
import styles from './UploadModal.module.css';

export const UploadModal = ({ isOpen, onClose }) => {
  const [file, setFile] = useState(null);
  const [uploadType, setUploadType] = useState('ADD');
  const [warehouseCode, setWarehouseCode] = useState('WH-01'); // Hardcoded default for this phase
  const [previewData, setPreviewData] = useState(null);
  const [confirmReplace, setConfirmReplace] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  
  const uploadMutation = useUploadInventory();

  const handleClose = () => {
    setFile(null);
    setPreviewData(null);
    setUploadType('ADD');
    onClose();
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setPreviewData(null);
    }
  };

  const handlePreview = () => {
    if (!file) return;
    uploadMutation.mutate(
      { warehouseCode, uploadType, file, preview: true },
      {
        onSuccess: (data) => {
          setPreviewData(data);
        }
      }
    );
  };

  const handleCommit = () => {
    if (uploadType === 'REPLACE') {
      setConfirmReplace(true);
    } else {
      setPasswordModalOpen(true);
    }
  };

  const executeCommit = (adminPassword) => {
    setConfirmReplace(false);
    uploadMutation.mutate(
      { warehouseCode, uploadType, file, preview: false, adminPassword },
      {
        onSuccess: () => {
          setPasswordModalOpen(false);
          handleClose();
        },
        onError: () => setPasswordModalOpen(false)
      }
    );
  };

  return (
    <>
      <Modal isOpen={isOpen} onClose={handleClose} title="Upload Inventory" maxWidth="600px">
        <div className={styles.container}>
          
          <div className={styles.options}>
            <div className={styles.field}>
              <label>Warehouse Code</label>
              <input 
                type="text" 
                value={warehouseCode} 
                onChange={e => setWarehouseCode(e.target.value)} 
                className={styles.input} 
              />
            </div>
            
            <div className={styles.field}>
              <label>Upload Mode</label>
              <div className={styles.radioGroup}>
                <label className={styles.radio}>
                  <input type="radio" name="uploadType" value="ADD" checked={uploadType === 'ADD'} onChange={() => setUploadType('ADD')} />
                  <span>Add Stock (Delta)</span>
                </label>
                <label className={styles.radio}>
                  <input type="radio" name="uploadType" value="REPLACE" checked={uploadType === 'REPLACE'} onChange={() => setUploadType('REPLACE')} />
                  <span className={styles.warningText}>Replace Inventory (Overwrite)</span>
                </label>
              </div>
            </div>
          </div>

          <div className={styles.fileUpload}>
            <input type="file" id="file-upload" accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel" onChange={handleFileChange} className={styles.hiddenInput} />
            <label htmlFor="file-upload" className={styles.dropzone}>
              <FiUploadCloud className={styles.uploadIcon} />
              <span className={styles.uploadText}>{file ? file.name : 'Click to select CSV or Excel file'}</span>
            </label>
          </div>

          {previewData && (
            <div className={styles.previewPanel}>
              <h4>Preview Results</h4>
              <div className={styles.previewStats}>
                <div className={styles.statBox}>
                  <span className={styles.statLabel}>Total Parsed</span>
                  <span className={styles.statValue}>{previewData.total_parsed}</span>
                </div>
                <div className={styles.statBox}>
                  <span className={styles.statLabel}>Valid Records</span>
                  <span className={`${styles.statValue} ${styles.success}`}>{previewData.valid_records_count}</span>
                </div>
                <div className={styles.statBox}>
                  <span className={styles.statLabel}>Errors</span>
                  <span className={`${styles.statValue} ${previewData.errors?.length > 0 ? styles.error : styles.success}`}>{previewData.errors?.length || 0}</span>
                </div>
              </div>
              
              {previewData.errors?.length > 0 && (
                <div className={styles.errorsList}>
                  <h5><FiAlertCircle /> Validation Errors</h5>
                  <ul>
                    {previewData.errors.map((err, i) => (
                      <li key={i}>{typeof err === 'string' ? err : `${err.row ? `Row ${err.row}: ` : ''}${err.error}`}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div className={styles.actions}>
            <Button variant="secondary" onClick={handleClose} disabled={uploadMutation.isPending}>Cancel</Button>
            
            {!previewData ? (
              <Button variant="primary" onClick={handlePreview} disabled={!file} isLoading={uploadMutation.isPending}>Preview Upload</Button>
            ) : (
              <Button variant="primary" onClick={handleCommit} disabled={!previewData.is_valid} isLoading={uploadMutation.isPending}>
                Commit Upload
              </Button>
            )}
          </div>
        </div>
      </Modal>

      <ConfirmationDialog 
        isOpen={confirmReplace}
        onClose={() => setConfirmReplace(false)}
        onConfirm={() => setPasswordModalOpen(true)}
        title="Confirm REPLACE"
        message="WARNING: You are about to REPLACE all inventory at this warehouse. All existing items not in this file will be set to 0. Are you sure?"
        confirmText="Yes, Replace Inventory"
        isDanger={true}
      />
      <AdminPasswordModal 
        isOpen={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
        onSubmit={executeCommit}
        actionName="upload inventory"
      />
    </>
  );
};

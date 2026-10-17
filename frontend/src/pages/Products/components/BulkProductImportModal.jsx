import React, { useState, useRef } from 'react';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import { productService } from '../../../services/products';
import { useBulkImportProducts } from '../../../hooks/useProducts';
import { FiUploadCloud, FiDownload, FiCheckCircle, FiAlertTriangle, FiFileText, FiX } from 'react-icons/fi';
import styles from './BulkProductImportModal.module.css';

export const BulkProductImportModal = ({ isOpen, onClose }) => {
  const [file, setFile] = useState(null);
  const [updateExisting, setUpdateExisting] = useState(false);
  const [initStock, setInitStock] = useState(true);
  const [previewData, setPreviewData] = useState(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const fileInputRef = useRef(null);

  const bulkImportMutation = useBulkImportProducts();

  const handleReset = () => {
    setFile(null);
    setPreviewData(null);
    setUpdateExisting(false);
    setInitStock(true);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setPreviewData(null);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      setIsDownloading(true);
      const blob = await productService.downloadTemplate();
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'product_import_template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      console.error('Failed to download template:', err);
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePreview = async () => {
    if (!file) return;
    try {
      setIsPreviewing(true);
      const res = await bulkImportMutation.mutateAsync({
        file,
        dryRun: true,
        updateExisting,
        initStock
      });
      setPreviewData(res);
    } catch (err) {
      console.error('Dry-run preview failed:', err);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!file) return;
    try {
      await bulkImportMutation.mutateAsync({
        file,
        dryRun: false,
        updateExisting,
        initStock
      });
      handleClose();
    } catch (err) {
      console.error('Bulk import execution failed:', err);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Bulk Product Import" maxWidth="640px">
      <div className={styles.container}>
        {/* Template Download Banner */}
        <div className={styles.templateBanner}>
          <div className={styles.templateInfo}>
            <span className={styles.templateTitle}>Excel Import Template</span>
            <span className={styles.templateDesc}>Download the standardized XLSX format with column guides and sample data.</span>
          </div>
          <Button 
            variant="secondary" 
            onClick={handleDownloadTemplate} 
            isLoading={isDownloading}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <FiDownload /> Download Template
          </Button>
        </div>

        {/* File Selection Zone */}
        {!file ? (
          <div 
            className={styles.dropzone}
            onClick={() => fileInputRef.current?.click()}
          >
            <FiUploadCloud className={styles.uploadIcon} />
            <div>
              <div className={styles.filePrompt}>Click or drag Excel/CSV file to upload</div>
              <div className={styles.fileSubprompt}>Supported formats: .xlsx, .xls, .csv</div>
            </div>
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".xlsx,.xls,.csv" 
              onChange={handleFileChange} 
            />
          </div>
        ) : (
          <div className={styles.fileSelected}>
            <div className={styles.fileSelectedInfo}>
              <FiFileText size={20} />
              <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
            </div>
            <Button variant="secondary" onClick={handleReset} style={{ padding: '4px 8px' }}>
              <FiX /> Change File
            </Button>
          </div>
        )}

        {/* Configuration Options */}
        <div className={styles.optionsGroup}>
          <label className={styles.checkboxLabel}>
            <input 
              type="checkbox" 
              checked={updateExisting} 
              onChange={(e) => { setUpdateExisting(e.target.checked); setPreviewData(null); }} 
            />
            <span>Update existing products if SKU already exists in catalog</span>
          </label>
          <label className={styles.checkboxLabel}>
            <input 
              type="checkbox" 
              checked={initStock} 
              onChange={(e) => { setInitStock(e.target.checked); setPreviewData(null); }} 
            />
            <span>Credit initial inventory stock into Central Warehouse (if Initial Stock column is present)</span>
          </label>
        </div>

        {/* Dry-run Preview Results */}
        {previewData && (
          <div className={styles.previewCard}>
            <div className={styles.previewHeader}>Import Preview Summary</div>
            <div className={styles.statsGrid}>
              <div className={styles.statBox}>
                <div className={`${styles.statValue} ${styles.statNew}`}>
                  {previewData.new_count ?? 0}
                </div>
                <div className={styles.statLabel}>New SKUs to Create</div>
              </div>
              <div className={styles.statBox}>
                <div className={`${styles.statValue} ${styles.statUpdate}`}>
                  {previewData.existing_count ?? 0}
                </div>
                <div className={styles.statLabel}>
                  {updateExisting ? 'Existing to Update' : 'Existing (Skipped)'}
                </div>
              </div>
              <div className={styles.statBox}>
                <div className={`${styles.statValue} ${styles.statInvalid}`}>
                  {previewData.invalid_count ?? 0}
                </div>
                <div className={styles.statLabel}>Invalid Rows</div>
              </div>
            </div>

            {previewData.new_skus?.length > 0 && (
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  New SKUs Identified ({previewData.new_skus.length}):
                </div>
                <div className={styles.skuPills}>
                  {previewData.new_skus.slice(0, 15).map(sku => (
                    <span key={sku} className={styles.skuPill}>{sku}</span>
                  ))}
                  {previewData.new_skus.length > 15 && (
                    <span className={styles.skuPill}>+{previewData.new_skus.length - 15} more</span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className={styles.actions}>
          <Button variant="secondary" onClick={handleClose} disabled={isPreviewing || bulkImportMutation.isPending}>
            Cancel
          </Button>
          {!previewData ? (
            <Button 
              variant="primary" 
              onClick={handlePreview} 
              disabled={!file} 
              isLoading={isPreviewing}
            >
              Preview Import (Dry Run)
            </Button>
          ) : (
            <Button 
              variant="primary" 
              onClick={handleConfirmImport} 
              isLoading={bulkImportMutation.isPending}
            >
              <FiCheckCircle style={{ marginRight: '6px' }} /> Confirm & Import {previewData.new_count + (updateExisting ? previewData.existing_count : 0)} Products
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  FiPrinter, 
  FiDownload, 
  FiArrowLeft, 
  FiRefreshCw, 
  FiCheckCircle, 
  FiAlertCircle,
  FiFileText,
  FiCopy
} from 'react-icons/fi';
import api from '../../services/api';
import InvoiceRenderer from '../../components/invoice/InvoiceRenderer';
import { downloadInvoicePdf } from '../../services/invoicePdfService';
import styles from './InvoicePreviewPage.module.css';

export default function InvoicePreviewPage() {
  const { saleId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const invoiceRef = useRef(null);

  const [invoice, setInvoice] = useState(location.state?.receipt || null);
  const [loading, setLoading] = useState(!location.state?.receipt);
  const [error, setError] = useState(null);
  const [retryingTally, setRetryingTally] = useState(false);
  const [showTallyModal, setShowTallyModal] = useState(false);
  const [tallyPayloads, setTallyPayloads] = useState(null);
  const [tallyPayloadFormat, setTallyPayloadFormat] = useState('XML');

  useEffect(() => {
    if (!invoice && saleId) {
      fetchInvoice();
    }
  }, [saleId, invoice]);

  const fetchInvoice = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/api/pos/sales/${saleId}`);
      if (response.data?.receipt) {
        setInvoice(response.data.receipt);
      } else {
        setError('Invoice data not found');
      }
    } catch (err) {
      console.error('Failed to fetch invoice:', err);
      const backendError = err.response?.data?.detail || err.message;
      setError(`Failed to load invoice: ${backendError}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRetryTally = async () => {
    if (!saleId) return;
    setRetryingTally(true);
    try {
      await api.post(`/api/pos/sales/${saleId}/retry-tally`);
      // Re-fetch invoice to get updated status
      await fetchInvoice();
    } catch (err) {
      console.error('Failed to retry Tally sync:', err);
      alert('Failed to retry Tally sync');
    } finally {
      setRetryingTally(false);
    }
  };

  const handlePreviewTally = async () => {
    if (!saleId) return;
    setShowTallyModal(true);
    if (!tallyPayloads) {
      try {
        const response = await api.get(`/api/pos/sales/${saleId}/tally-payload`);
        setTallyPayloads(response.data);
      } catch (err) {
        console.error('Failed to fetch tally payload:', err);
      }
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPdf = () => {
    if (invoiceRef.current && invoice) {
      downloadInvoicePdf(invoiceRef.current, invoice.invoice_number || saleId);
    }
  };

  if (loading) {
    return <div className={styles.loadingContainer}>Loading invoice...</div>;
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <p className={styles.errorMessage}>{error}</p>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <FiArrowLeft /> Go Back
        </button>
      </div>
    );
  }

  if (!invoice) return null;

  const isB2b = invoice.invoice_type === 'B2B' || invoice.customer?.gstin;
  const tallyStatus = invoice.tally?.status || 'PENDING';
  const showRetry = isB2b && (tallyStatus === 'FAILED' || tallyStatus === 'PENDING');

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <button className={styles.actionButton} onClick={() => navigate(-1)}>
            <FiArrowLeft /> Back
          </button>
        </div>
        
        <div className={styles.toolbarCenter}>
          {isB2b && (
            <div className={styles.tallyStatusWrapper}>
              <span className={`${styles.badge} ${styles[tallyStatus.toLowerCase()]}`}>
                {tallyStatus === 'SUCCESS' && <FiCheckCircle />}
                {tallyStatus === 'FAILED' && <FiAlertCircle />}
                {tallyStatus === 'PENDING' && <FiRefreshCw />}
                Tally: {tallyStatus}
              </span>
              {showRetry && (
                <button 
                  className={styles.retryButton} 
                  onClick={handleRetryTally}
                  disabled={retryingTally}
                >
                  <FiRefreshCw className={retryingTally ? styles.spin : ''} />
                  Retry Sync
                </button>
              )}
              <button className={styles.actionButton} onClick={handlePreviewTally}>
                <FiFileText /> Preview Tally
              </button>
            </div>
          )}
        </div>

        <div className={styles.toolbarRight}>
          <button className={styles.actionButton} onClick={handlePrint}>
            <FiPrinter /> Print
          </button>
          <button className={styles.actionButton} onClick={handleDownloadPdf}>
            <FiDownload /> Download PDF
          </button>
        </div>
      </div>

      <div className={styles.invoiceWrapper}>
        <div className={styles.invoicePaper} ref={invoiceRef}>
          <InvoiceRenderer invoice={invoice} />
        </div>
      </div>

      {showTallyModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3>Tally Payload Preview</h3>
              <button onClick={() => setShowTallyModal(false)} className={styles.closeButton}>&times;</button>
            </div>
            
            {tallyPayloads ? (
              <div className={styles.modalBody}>
                <div className={styles.tabs}>
                  <button 
                    className={tallyPayloadFormat === 'XML' ? styles.activeTab : styles.tab} 
                    onClick={() => setTallyPayloadFormat('XML')}
                  >
                    XML
                  </button>
                  <button 
                    className={tallyPayloadFormat === 'JSON' ? styles.activeTab : styles.tab} 
                    onClick={() => setTallyPayloadFormat('JSON')}
                  >
                    JSON
                  </button>
                </div>
                
                <pre className={styles.payloadPre}>
                  {tallyPayloadFormat === 'XML' ? tallyPayloads.xml : tallyPayloads.json}
                </pre>
                
                <div className={styles.modalActions}>
                  <button 
                    className={styles.secondaryButton} 
                    onClick={() => navigator.clipboard.writeText(tallyPayloadFormat === 'XML' ? tallyPayloads.xml : tallyPayloads.json)}
                  >
                    <FiCopy /> Copy
                  </button>
                  <button 
                    className={styles.secondaryButton}
                    onClick={() => {
                       const blob = new Blob([tallyPayloadFormat === 'XML' ? tallyPayloads.xml : tallyPayloads.json], {type: 'text/plain'});
                       const url = URL.createObjectURL(blob);
                       const a = document.createElement('a');
                       a.href = url;
                       a.download = `tally_payload_${saleId}.${tallyPayloadFormat.toLowerCase()}`;
                       a.click();
                    }}
                  >
                    <FiDownload /> Download
                  </button>
                  <button 
                    className={styles.primaryButton} 
                    onClick={() => { setShowTallyModal(false); handleRetryTally(); }}
                  >
                    <FiRefreshCw /> Send to Tally
                  </button>
                </div>
              </div>
            ) : (
              <div className={styles.modalBody}>Loading payload...</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

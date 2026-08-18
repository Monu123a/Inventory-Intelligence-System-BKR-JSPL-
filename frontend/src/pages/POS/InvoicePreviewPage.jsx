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
  FiCopy,
  FiEye
} from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { posService } from '../../services/pos';
import { handleApiError } from '../../utils/errorHandler';
import InvoiceRenderer from '../../components/invoice/InvoiceRenderer';
import { downloadInvoicePdf } from '../../services/invoicePdfService';
import html2pdf from 'html2pdf.js';
import styles from './InvoicePreviewPage.module.css';

export default function InvoicePreviewPage() {
  const { saleId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const invoiceRef = useRef(null);

  const { data: invoice, isLoading: loading, error: fetchError } = useQuery({
    queryKey: ['sale', saleId],
    queryFn: () => posService.getSaleById(saleId),
    initialData: location.state?.receipt,
  });

  const error = fetchError ? (fetchError.response?.data?.detail || fetchError.message) : null;

  const [retryingTally, setRetryingTally] = useState(false);
  const [showTallyModal, setShowTallyModal] = useState(false);
  const [tallyPayloadFormat, setTallyPayloadFormat] = useState('XML');

  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailAddress, setEmailAddress] = useState('');
  const [emailing, setEmailing] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [emailSuccess, setEmailSuccess] = useState('');

  const { data: tallyPayloads, refetch: fetchTallyPayloads } = useQuery({
    queryKey: ['tallyPayload', saleId],
    queryFn: () => posService.getTallyPayload(saleId),
    enabled: false,
  });

  const retryTallyMutation = useMutation({
    mutationFn: posService.retryTallySync,
    onMutate: () => setRetryingTally(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sale', saleId] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
    },
    onError: (err) => handleApiError(err, 'Failed to retry Tally sync'),
    onSettled: () => setRetryingTally(false),
  });

  const handleRetryTally = () => {
    if (!saleId) return;
    retryTallyMutation.mutate(saleId);
  };

  const handlePreviewTally = () => {
    if (!saleId) return;
    setShowTallyModal(true);
    if (!tallyPayloads) {
      fetchTallyPayloads();
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

  const handleOpenEmailModal = () => {
    setEmailAddress(invoice?.customer?.email || '');
    setEmailError('');
    setEmailSuccess('');
    setShowEmailModal(true);
  };

  const emailMutation = useMutation({
    mutationFn: posService.emailInvoice,
    onMutate: () => setEmailing(true),
    onSuccess: () => {
      setEmailSuccess('Email sent successfully!');
      setTimeout(() => setShowEmailModal(false), 2000);
    },
    onError: (err) => {
      setEmailError(err.response?.data?.detail || err.message || 'Failed to send email');
    },
    onSettled: () => setEmailing(false),
  });

  const handleEmailInvoice = async () => {
    if (!emailAddress) {
      setEmailError('Please enter an email address.');
      return;
    }
    
    setEmailError('');
    setEmailSuccess('');
    
    try {
      // 1. Generate PDF blob
      const opt = {
        margin:       0,
        filename:     `Invoice_${invoice.invoice_number || saleId}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2 },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
      };
      
      const pdfBlob = await html2pdf().set(opt).from(invoiceRef.current).output('blob');
      
      // 2. Create FormData
      const formData = new FormData();
      formData.append('file', pdfBlob, opt.filename);
      formData.append('to_email', emailAddress);
      
      emailMutation.mutate({ saleId: invoice.id, formData });
    } catch (err) {
      console.error('Failed to generate PDF for email:', err);
      setEmailError('Failed to generate PDF');
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
          <button className={styles.primaryButton} onClick={handleOpenEmailModal}>
            Email Customer
          </button>
        </div>
      </div>

      <div className={styles.invoiceWrapper}>
        <div className={styles.invoicePaper} ref={invoiceRef}>
          <InvoiceRenderer invoice={invoice} />
        </div>
        
        {invoice.related_returns && invoice.related_returns.length > 0 && (
          <div className={styles.relatedReturnsSection}>
            <h3 style={{ marginTop: '24px', marginBottom: '16px', color: '#1e293b' }}>Related Sales Returns</h3>
            <div className={styles.returnsGrid} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {invoice.related_returns.map(ret => (
                <div key={ret.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                  <div>
                    <div style={{ fontWeight: '600', color: '#0f172a' }}>Return #{ret.return_number}</div>
                    <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                      Date: {new Date(ret.date).toLocaleDateString()} &bull; Qty: {ret.returned_quantity} &bull; Status: <span style={{ fontWeight: '600', color: ret.status === 'Completed' ? '#16a34a' : '#ea580c' }}>{ret.status}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => navigate(`/sales-returns/${ret.id}`)}
                    style={{ padding: '8px 16px', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#334155' }}
                  >
                    <FiEye /> View Return
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
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

      {showEmailModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent} style={{ maxWidth: '400px' }}>
            <div className={styles.modalHeader}>
              <h3>Email Invoice</h3>
              <button onClick={() => setShowEmailModal(false)} className={styles.closeButton}>&times;</button>
            </div>
            
            <div className={styles.modalBody}>
              <div className={styles.formGroup}>
                <label>Customer Email</label>
                <input 
                  type="email" 
                  value={emailAddress} 
                  onChange={e => setEmailAddress(e.target.value)}
                  placeholder="customer@example.com"
                  className={styles.inputField}
                  autoFocus
                />
              </div>
              
              {emailError && <div className={styles.errorText} style={{ color: 'red', marginTop: '10px' }}>{emailError}</div>}
              {emailSuccess && <div className={styles.successText} style={{ color: 'green', marginTop: '10px' }}>{emailSuccess}</div>}
              
              <div className={styles.modalActions} style={{ marginTop: '20px' }}>
                <button 
                  className={styles.secondaryButton} 
                  onClick={() => setShowEmailModal(false)}
                  disabled={emailing}
                >
                  Cancel
                </button>
                <button 
                  className={styles.primaryButton} 
                  onClick={handleEmailInvoice}
                  disabled={emailing}
                >
                  {emailing ? 'Sending...' : 'Send Email'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

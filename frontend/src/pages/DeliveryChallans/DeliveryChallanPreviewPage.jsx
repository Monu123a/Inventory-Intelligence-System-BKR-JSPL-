import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  FiPrinter, 
  FiDownload, 
  FiArrowLeft
} from 'react-icons/fi';
import api from '../../services/api';
import DeliveryChallanRenderer from '../../components/delivery-challans/DeliveryChallanRenderer';
import { downloadInvoicePdf } from '../../services/invoicePdfService';
import styles from '../POS/InvoicePreviewPage.module.css'; // Reusing invoice preview styles

export default function DeliveryChallanPreviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const challanRef = useRef(null);

  const [challan, setChallan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (id) {
      fetchChallan();
    }
  }, [id]);

  const fetchChallan = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/api/delivery-challans/${id}`);
      setChallan(response.data);
    } catch (err) {
      console.error('Failed to fetch challan:', err);
      const backendError = err.response?.data?.detail || err.message;
      setError(`Failed to load challan: ${backendError}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = async () => {
    window.print();
    // Update print count in background
    try {
      await api.post(`/api/delivery-challans/${id}/print`);
      fetchChallan(); // refresh print count silently
    } catch (e) {
      console.error('Failed to record print action', e);
    }
  };

  const handleDownloadPdf = () => {
    if (challanRef.current && challan) {
      downloadInvoicePdf(challanRef.current, challan.challan_number || id);
    }
  };

  if (loading) {
    return <div className={styles.loadingContainer}>Loading Delivery Challan...</div>;
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

  if (!challan) return null;

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <button className={styles.actionButton} onClick={() => navigate('/delivery-challans')}>
            <FiArrowLeft /> Back to List
          </button>
        </div>
        
        <div className={styles.toolbarCenter}>
           {/* Can add status badges here if needed */}
           <span style={{ fontWeight: '500', color: '#666' }}>
             Status: <strong style={{ color: '#000' }}>{challan.status}</strong> 
             &nbsp;|&nbsp; Prints: {challan.print_count}
           </span>
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
        <div className={styles.invoicePaper} ref={challanRef}>
          <DeliveryChallanRenderer challan={challan} />
        </div>
      </div>
    </div>
  );
}

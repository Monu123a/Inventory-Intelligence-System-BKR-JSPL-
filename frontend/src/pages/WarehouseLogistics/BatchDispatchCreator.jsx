import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { 
  CheckCircle, ChevronRight, ArrowRight, Package, 
  MapPin, Truck, FileText, Check, AlertTriangle, Building2
} from 'lucide-react';
import { useLocation } from 'react-router-dom';
import styles from './BatchDispatchCreator.module.css';
import InvoiceRenderer from '../../components/invoice/InvoiceRenderer';
import DeliveryChallanRenderer from '../../components/delivery-challans/DeliveryChallanRenderer';
import useCompanyStore from '../../stores/useCompanyStore';

const BatchDispatchCreator = () => {
  const { currentCompany } = useCompanyStore();
  const isBkr = currentCompany?.name?.toLowerCase().includes('bkr') || currentCompany?.code === 'BKR';
  
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const defaultSource = isBkr ? 'BKR' : 'CENTRAL';

  const [step, setStep] = useState(1);
  const [sourceWarehouse, setSourceWarehouse] = useState(defaultSource);
  const [selectedHub, setSelectedHub] = useState('');
  const [selectedFC, setSelectedFC] = useState('');
  
  const [hubs, setHubs] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);

  // Products
  const [inventory, setInventory] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [products, setProducts] = useState([]); // Will store items with transferQty > 0
  const [loadingInventory, setLoadingInventory] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        let headers = {};
        if (isBkr) {
          const compRes = await api.get('/api/companies');
          const jsplCompany = compRes.data.find(c => c.code === 'JSPL');
          if (jsplCompany) {
            headers = { 'X-Company-Id': jsplCompany.id };
          }
        }

        const [hubsRes, whRes] = await Promise.all([
          api.get('/api/state-hubs', { headers }),
          api.get('/api/warehouses', { headers })
        ]);
        setHubs(hubsRes.data || []);
        setWarehouses(whRes.data || []);
      } catch (err) {
        console.error('Failed to load destinations', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Fetch Inventory when entering Step 4
  useEffect(() => {
    if (step === 4) {
      const fetchInventory = async () => {
        setLoadingInventory(true);
        try {
          const res = await api.get(`/api/fc-dispatches/inventory?source_type=${sourceWarehouse}`);
          // Preserve existing transfer quantities if they exist
          const loadedInv = res.data.map(item => {
            const existing = products.find(p => p.id === item.id);
            return { ...item, transferQty: existing ? existing.transferQty : '' };
          });
          setInventory(loadedInv);
        } catch (err) {
          console.error('Failed to load inventory', err);
        } finally {
          setLoadingInventory(false);
        }
      };
      fetchInventory();
    }
  }, [step, sourceWarehouse]);

  const handleQtyChange = (id, val) => {
    const numVal = val === '' ? '' : parseInt(val, 10);
    setInventory(prev => prev.map(item => {
      if (item.id === id) {
        return { ...item, transferQty: numVal > item.currentStock ? item.currentStock : numVal };
      }
      return item;
    }));
  };

  const handleProceedToValidation = () => {
    const selected = inventory.filter(item => item.transferQty > 0);
    setProducts(selected);
    setStep(5);
  };

  const nextStep = () => setStep(s => s + 1);
  const prevStep = () => setStep(s => s - 1);

  // Helper to build mock snapshot data for Invoice/Challan rendering
  const buildMockInvoice = () => {
    const destFC = warehouses.find(w => w.id === selectedFC);
    const destHub = hubs.find(h => h.id === selectedHub) || destFC;
    
    // In actual implementation, backend generates these numbers
    const mockInvNo = `PI-${Math.floor(Math.random() * 10000)}`;
    const mockDate = new Date().toISOString();
    
    const seller = {
      name: sourceWarehouse === 'CENTRAL' ? 'Central Warehouse (VSHB)' : 'BKR Main Warehouse',
      gstin: '07AABCU9603R1ZM',
      address: 'Industrial Area, Phase 1',
      state: 'Haryana',
      state_code: '06'
    };
    
    const buyer = {
      name: destHub?.hub_name || 'Destination Hub',
      gstin: destHub?.gstin || 'UNREGISTERED',
      address: destHub?.address || 'Billing Address',
      state: destHub?.state || 'Destination State',
      state_code: destHub?.state_code || '99',
      place_of_supply: destHub?.state || ''
    };

    const shipping = {
      name: destFC?.name || `FC ID: ${selectedFC}`,
      gstin: destHub?.gstin || 'UNREGISTERED', // Hub GSTIN
      address: destFC?.address || destHub?.address || 'Shipping Address',
      state: destFC?.state || destHub?.state || 'Destination State',
      state_code: destFC?.state_code || destHub?.state_code || '99'
    };

    let totalTaxable = 0;
    let totalTax = 0;
    const isInterState = seller.state !== buyer.state;

    const mockItems = products.map((p, i) => {
      // Mock pricing (since we don't fetch price in inventory yet for this wizard)
      const unit_price = 500 + i * 100;
      const taxable = p.transferQty * unit_price;
      const tax_rate = 18;
      const tax_amount = taxable * (tax_rate / 100);
      const total = taxable + tax_amount;
      
      totalTaxable += taxable;
      totalTax += tax_amount;

      return {
        product_name_snapshot: p.name,
        sku_snapshot: p.sku,
        hsn_snapshot: '8467',
        unit_snapshot: 'PCS',
        quantity: p.transferQty,
        unit_price: unit_price,
        tax_rate: tax_rate,
        tax_amount: tax_amount,
        total_price: total
      };
    });

    const mockInvoice = {
      invoice_number: mockInvNo,
      date: mockDate,
      invoice_type: 'B2B',
      company: seller,
      customer: buyer,
      shipping: shipping,
      items: mockItems,
      totals: {
        total_taxable: totalTaxable,
        total_tax: totalTax,
        grand_total: totalTaxable + totalTax,
        igst_total: isInterState ? totalTax : 0,
        cgst_total: isInterState ? 0 : totalTax / 2,
        sgst_total: isInterState ? 0 : totalTax / 2
      }
    };
    
    const mockChallan = {
      challan_number: `DC-${Math.floor(Math.random() * 10000)}`,
      challan_date: mockDate,
      seller_snapshot: seller,
      buyer_snapshot: buyer,
      shipping_snapshot: shipping,
      items: mockItems
    };
    
    return { mockInvoice, mockChallan };
  };

  const handleSubmit = async () => {
    try {
      await api.post('/api/fc-dispatches', {
        warehouse_ids: [selectedFC],
        hub_id: selectedHub ? parseInt(selectedHub, 10) : null,
        source_type: sourceWarehouse === 'CENTRAL' ? 'CENTRAL_WAREHOUSE' : 'BKR',
        items: products.map(p => ({ product_id: p.id, quantity: p.transferQty }))
      });
      alert('Dispatch created successfully');
      setStep(1);
      setSelectedHub('');
      setSelectedFC('');
    } catch (err) {
      console.error(err);
      alert('Error creating dispatch');
    }
  };

  const steps = [
    { id: 1, name: 'Source' },
    { id: 2, name: 'State Hub' },
    { id: 3, name: 'Warehouse / FC' },
    { id: 4, name: 'Products' },
    { id: 5, name: 'Validation' },
    { id: 6, name: 'Invoice' },
    { id: 7, name: 'Challan' },
    { id: 8, name: 'Confirm' }
  ];

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>FC Dispatch Wizard</h1>
        
        {/* Progress Bar */}
        <div className={styles.progressContainer}>
          {/* Progress bar background line */}
          <div className={styles.progressLine} />
          {steps.map((s, i) => (
            <div key={s.id} className={styles.stepNode}>
              <div className={`${styles.stepIcon} ${
                step >= s.id ? styles.stepIconActive : styles.stepIconInactive
              } shadow-sm`}>
                {step > s.id ? <Check size={16} /> : s.id}
              </div>
              <span className={`${styles.stepLabel} ${step >= s.id ? styles.stepLabelActive : styles.stepLabelInactive}`}>
                {s.name}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.contentCard}>
        <div className={styles.contentInner}>
          
          {/* Step 1: Source */}
          {step === 1 && (
            <div>
              <h2 className={styles.stepTitle}><MapPin /> Select Source Warehouse</h2>
              <p className={styles.stepSubtitle}>Where is the stock coming from?</p>
              
              <div className={styles.sourceGrid}>
                {/* BKR Card - Only show for BKR Company */}
                {isBkr && (
                  <div 
                    className={`${styles.sourceCard} ${sourceWarehouse === 'BKR' ? styles.sourceCardBkrActive : ''}`}
                    onClick={() => setSourceWarehouse('BKR')}
                  >
                    <div className={styles.sourceHeader}>
                      <div className={styles.sourceTitleGroup}>
                        <div className={`${styles.sourceIconBox} ${sourceWarehouse === 'BKR' ? styles.sourceIconBoxBkrActive : ''}`}>
                          <Building2 />
                        </div>
                        <div>
                          <h3 className={`${styles.sourceTitle} ${sourceWarehouse === 'BKR' ? styles.sourceTitleBkrActive : ''}`}>BKR Main Warehouse</h3>
                          <p className={styles.sourceSubtitle}>External Replenishment</p>
                        </div>
                      </div>
                      {sourceWarehouse === 'BKR' && (
                        <div className={`${styles.sourceCheck} ${styles.sourceCheckBkr}`}>
                          <Check size={16} strokeWidth={3} />
                        </div>
                      )}
                    </div>
                    
                    <div className={styles.sourceDesc}>
                      Use this option to dispatch fresh stock from the BKR main manufacturing hub directly to regional fulfillment centers.
                    </div>
                  </div>
                )}

                {/* Central Card - Only show for JSPL Company */}
                {!isBkr && (
                  <div 
                    className={`${styles.sourceCard} ${sourceWarehouse === 'CENTRAL' ? styles.sourceCardCentralActive : ''}`}
                    onClick={() => setSourceWarehouse('CENTRAL')}
                  >
                    <div className={styles.sourceHeader}>
                      <div className={styles.sourceTitleGroup}>
                        <div className={`${styles.sourceIconBox} ${sourceWarehouse === 'CENTRAL' ? styles.sourceIconBoxCentralActive : ''}`}>
                          <Truck />
                        </div>
                        <div>
                          <h3 className={`${styles.sourceTitle} ${sourceWarehouse === 'CENTRAL' ? styles.sourceTitleCentralActive : ''}`}>Central Warehouse</h3>
                          <p className={styles.sourceSubtitle}>Internal Distribution</p>
                        </div>
                      </div>
                      {sourceWarehouse === 'CENTRAL' && (
                        <div className={`${styles.sourceCheck} ${styles.sourceCheckCentral}`}>
                          <Check size={16} strokeWidth={3} />
                        </div>
                      )}
                    </div>
                    
                    <div className={styles.sourceDesc}>
                      Use this option for regular intra-company distribution from the VSHB Central Hub to smaller regional FCs.
                    </div>
                  </div>
                )}
              </div>

              <div className={styles.actionRow}>
                <button 
                  className={styles.btnPrimary}
                  onClick={() => setStep(2)}
                >
                  Continue to Destination
                  <ArrowRight size={18} />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Hub */}
          {step === 2 && (
            <div>
              <h2 className={styles.stepTitle}><Truck color="#2563eb" /> Select State Hub</h2>
              <div className={styles.grid}>
                {hubs.map(hub => (
                  <div 
                    key={hub.id}
                    className={`${styles.card} ${selectedHub === hub.id ? styles.cardActive : ''}`}
                    onClick={() => {
                      setSelectedHub(hub.id);
                      setSelectedFC('');
                    }}
                  >
                    <h3 className={styles.cardTitle}>{hub.hub_name}</h3>
                    <p className={styles.cardSubtitle}>Code: <strong>{hub.hub_code}</strong></p>
                  </div>
                ))}
                {hubs.length === 0 && <p>No hubs available or still loading...</p>}
              </div>
              <div className={styles.actionRow}>
                <button className={styles.btnPrimary} onClick={() => setStep(1)} style={{marginRight: 'auto', backgroundColor: '#6b7280'}}>Back</button>
                <button 
                  className={styles.btnPrimary} 
                  onClick={() => {
                    const hubFCs = warehouses.filter(w => w.hub_id === selectedHub && w.status?.toUpperCase() === 'ACTIVE');
                    if (hubFCs.length === 0) {
                      alert('No active warehouse is available under this State Hub.');
                    } else if (hubFCs.length === 1) {
                      setSelectedFC(hubFCs[0].id);
                      setStep(4);
                    } else {
                      setStep(3);
                    }
                  }} 
                  disabled={!selectedHub}
                >
                  Next Step
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Warehouse / FC */}
          {step === 3 && (
            <div>
              <h2 className={styles.stepTitle}><Package color="#2563eb" /> Select Warehouse / FC</h2>
              <div className={styles.grid}>
                {warehouses.filter(w => w.hub_id === selectedHub && w.status?.toUpperCase() === 'ACTIVE').map(fc => (
                  <div 
                    key={fc.id}
                    className={`${styles.card} ${selectedFC === fc.id ? styles.cardActive : ''}`}
                    onClick={() => setSelectedFC(fc.id)}
                  >
                    <h3 className={styles.cardTitle}>{fc.name}</h3>
                    <div className={styles.cardSubtitle}>
                      <p>Code: <strong>{fc.code}</strong></p>
                      <p>GSTIN: <strong>{fc.gstin || 'N/A'}</strong></p>
                    </div>
                  </div>
                ))}
                {warehouses.filter(w => w.hub_id === selectedHub && w.status?.toUpperCase() === 'ACTIVE').length === 0 && (
                  <p>No active Warehouse/FC found for this hub.</p>
                )}
              </div>
              <div className={styles.actionRow}>
                <button className={styles.btnPrimary} onClick={() => setStep(2)} style={{marginRight: 'auto', backgroundColor: '#6b7280'}}>Back</button>
                <button className={styles.btnPrimary} onClick={() => setStep(4)} disabled={!selectedFC}>Next Step</button>
              </div>
            </div>
          )}

          {/* Step 4: Products */}
          {step === 4 && (
            <div>
              <h2 className={styles.stepTitle}><Package color="#2563eb" /> Select Products & Quantities</h2>
              
              <div style={{ marginBottom: '16px' }}>
                <input 
                  type="text" 
                  placeholder="Search products..." 
                  className={styles.inputField} 
                  style={{ width: '100%', maxWidth: '400px' }}
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
              </div>

              {loadingInventory ? (
                <p>Loading inventory from {sourceWarehouse} warehouse...</p>
              ) : (
                <div className={styles.tableContainer}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Product Name</th>
                        <th style={{textAlign: 'center'}}>Current Stock</th>
                        <th style={{textAlign: 'center'}}>Recommended Qty</th>
                        <th>Transfer Qty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inventory.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.sku.toLowerCase().includes(searchTerm.toLowerCase())).map((p) => (
                        <tr key={p.id}>
                          <td style={{fontWeight: '500'}}>{p.name} <br/><span style={{fontSize: '12px', color: '#6b7280'}}>{p.sku}</span></td>
                          <td style={{textAlign: 'center', fontFamily: 'monospace'}}>{p.currentStock}</td>
                          <td style={{textAlign: 'center', fontFamily: 'monospace', color: '#2563eb', fontWeight: 'bold'}}>{p.recommended}</td>
                          <td>
                            <input 
                              type="number" 
                              className={styles.inputField}
                              value={p.transferQty}
                              min="0"
                              max={p.currentStock}
                              onChange={(e) => handleQtyChange(p.id, e.target.value)}
                            />
                          </td>
                        </tr>
                      ))}
                      {inventory.length === 0 && (
                        <tr>
                          <td colSpan="4" style={{textAlign: 'center', padding: '24px'}}>No inventory available at {sourceWarehouse} warehouse.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
              
              <div className={styles.actionRow}>
                <button className={styles.btnPrimary} onClick={() => setStep(3)} style={{marginRight: 'auto', backgroundColor: '#6b7280'}}>Back</button>
                <button className={styles.btnPrimary} onClick={handleProceedToValidation} disabled={inventory.filter(i => i.transferQty > 0).length === 0}>Validate Stock</button>
              </div>
            </div>
          )}

          {/* Step 5: Validation */}
          {step === 5 && (
            <div>
              <h2 className={styles.stepTitle}><CheckCircle color="#10b981" /> Inventory Validation</h2>
              <div style={{backgroundColor: '#ecfdf5', border: '1px solid #a7f3d0', padding: '20px', borderRadius: '8px', display: 'flex', gap: '16px', alignItems: 'flex-start'}}>
                <CheckCircle color="#10b981" size={24} style={{marginTop: '2px'}} />
                <div>
                  <h3 style={{fontWeight: 'bold', color: '#065f46', margin: '0 0 4px 0'}}>All Stock Validated</h3>
                  <p style={{color: '#047857', margin: 0}}>Sufficient inventory is available at {sourceWarehouse} for this dispatch request.</p>
                </div>
              </div>
              <div style={{marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '12px'}}>
                {products.map(p => (
                  <div key={p.id} style={{display: 'flex', justifyContent: 'space-between', padding: '16px', border: '1px solid #f3f4f6', borderRadius: '8px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)'}}>
                    <span style={{fontWeight: '500'}}>{p.name}</span>
                    <span style={{fontFamily: 'monospace', backgroundColor: '#f3f4f6', padding: '4px 8px', borderRadius: '4px'}}>
                      Req: <strong style={{color: '#2563eb'}}>{p.transferQty}</strong> / Avail: {p.currentStock}
                    </span>
                  </div>
                ))}
              </div>
              <div className={styles.actionRow}>
                <button className={styles.btnPrimary} onClick={() => setStep(4)} style={{marginRight: 'auto', backgroundColor: '#6b7280'}}>Back</button>
                <button className={styles.btnPrimary} onClick={() => setStep(6)}>View Invoice Preview</button>
              </div>
            </div>
          )}

          {/* Step 6: Invoice Preview */}
          {step === 6 && (
            <div>
              <h2 className={styles.stepTitle}><FileText color="#2563eb" /> Proforma Invoice Preview</h2>
              
              <div style={{ backgroundColor: '#f9fafb', padding: '20px', border: '1px solid #e5e7eb', borderRadius: '8px', marginBottom: '24px', overflowX: 'auto' }}>
                <InvoiceRenderer invoice={buildMockInvoice().mockInvoice} />
              </div>

              <div className={styles.actionRow}>
                <button className={styles.btnPrimary} onClick={() => setStep(5)} style={{marginRight: 'auto', backgroundColor: '#6b7280'}}>Back</button>
                <button className={styles.btnPrimary} onClick={() => setStep(7)}>View Delivery Challan</button>
              </div>
            </div>
          )}

          {/* Step 7: Challan Preview */}
          {step === 7 && (
            <div>
              <h2 className={styles.stepTitle}><Truck color="#2563eb" /> Delivery Challan Preview</h2>
              
              <div style={{ backgroundColor: '#f9fafb', padding: '20px', border: '1px solid #e5e7eb', borderRadius: '8px', marginBottom: '24px', overflowX: 'auto' }}>
                <DeliveryChallanRenderer challan={buildMockInvoice().mockChallan} />
              </div>

              <div className={styles.actionRow}>
                <button className={styles.btnPrimary} onClick={() => setStep(6)} style={{marginRight: 'auto', backgroundColor: '#6b7280'}}>Back</button>
                <button className={styles.btnPrimary} onClick={() => setStep(8)}>Proceed to Confirm</button>
              </div>
            </div>
          )}

          {/* Step 8: Confirm */}
          {step === 8 && (
            <div style={{maxWidth: '600px', margin: '32px auto 0', textAlign: 'center', padding: '48px 0'}}>
              <div style={{width: '80px', height: '80px', backgroundColor: '#eff6ff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', border: '1px solid #dbeafe', boxShadow: '0 1px 2px rgba(0,0,0,0.05)'}}>
                <AlertTriangle color="#3b82f6" size={40} />
              </div>
              <h2 style={{fontSize: '30px', fontWeight: 'bold', color: '#1f2937', marginBottom: '16px'}}>Confirm Batch Dispatch</h2>
              <p style={{fontSize: '18px', color: '#4b5563', lineHeight: 1.6, marginBottom: '32px'}}>
                You are about to dispatch <strong style={{color: '#111827'}}>{products.reduce((acc, p) => acc + p.transferQty, 0)}</strong> items from <strong style={{color: '#111827'}}>{sourceWarehouse === 'CENTRAL' ? 'Central Warehouse' : 'BKR Main Warehouse'}</strong> to FC <strong style={{color: '#111827'}}>{warehouses.find(w => w.id === selectedFC)?.name || `#${selectedFC}`}</strong>.
              </p>
              <div style={{backgroundColor: '#fefce8', color: '#854d0e', padding: '16px', borderRadius: '8px', border: '1px solid #fef08a', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '32px', fontSize: '14px'}}>
                <CheckCircle size={16} /> All documents will be generated and logged automatically.
              </div>
              <div>
                <button 
                  style={{backgroundColor: '#2563eb', color: 'white', padding: '16px 32px', borderRadius: '12px', fontWeight: 'bold', fontSize: '18px', border: 'none', cursor: 'pointer', width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'}}
                  onClick={handleSubmit}
                >
                  <Package /> Generate Final Dispatch Documents
                </button>
              </div>
              <div className={styles.actionRow} style={{marginTop: '24px', justifyContent: 'center'}}>
                <button className={styles.btnPrimary} onClick={() => setStep(7)} style={{backgroundColor: '#6b7280'}}>Back to Preview</button>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
};

export default BatchDispatchCreator;

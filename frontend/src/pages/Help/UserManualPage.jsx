import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import { 
  FiShoppingCart, 
  FiTool, 
  FiPackage, 
  FiBriefcase, 
  FiArrowRight,
  FiSearch,
  FiHelpCircle,
  FiMail,
  FiPhoneCall,
  FiMessageSquare,
  FiChevronDown,
  FiChevronUp,
  FiUploadCloud,
  FiDownload
} from 'react-icons/fi';
import styles from './UserManualPage.module.css';

const UserManualPage = () => {
  const navigate = useNavigate();
  const [activeRole, setActiveRole] = useState('biller');
  const [searchQuery, setSearchQuery] = useState('');
  const [openFaq, setOpenFaq] = useState(null);

  const ROLES = [
    { id: 'biller', name: 'Billing & POS', icon: FiShoppingCart },
    { id: 'technician', name: 'Service & Repair', icon: FiTool },
    { id: 'warehouse', name: 'Warehouse & Logistics', icon: FiPackage },
    { id: 'accounting', name: 'Tally & Accounts', icon: FiBriefcase },
    { id: 'uploads', name: 'Data Uploads & Templates', icon: FiUploadCloud },
  ];

  const MANUAL_CONTENT = {
    biller: {
      title: "Point of Sale (POS) Guide",
      description: "How to quickly generate sales, add products to cart, and process customer invoices.",
      steps: [
        { title: "Search Products", desc: "Use the search bar to find products by SKU or Name. Click to add them to your cart." },
        { title: "Adjust Cart", desc: "Change the quantity. Taxes (GST) are automatically calculated based on the product's master configuration." },
        { title: "Customer Details", desc: "Enter the Customer's Name, Phone, and Address (this is required for tax invoices)." },
        { title: "Checkout", desc: "Click Complete Sale. Inventory is deducted automatically from your store's stock." }
      ],
      actionText: "Open POS Workstation",
      actionRoute: ROUTES.POS
    },
    technician: {
      title: "Service & Repair Workflow",
      description: "Manage customer repairs, job cards, and generate final service tax invoices.",
      steps: [
        { title: "Log a Service Record", desc: "Create a ticket capturing customer details, machine type, and their exact complaint." },
        { title: "Create Job Card", desc: "Assign the job to a technician. Status becomes IN_PROGRESS." },
        { title: "Add Spares & Labor", desc: "Add inventory parts or manual labor charges to the Job Card. Mark as COMPLETED." },
        { title: "Generate Invoice", desc: "Once completed, generate the final Tax Invoice. The job card is locked." }
      ],
      actionText: "Open Service Dashboard",
      actionRoute: ROUTES.SERVICE_DASHBOARD
    },
    warehouse: {
      title: "Warehouse & Logistics",
      description: "Manage stock movements, inter-company transfers, FC dispatches, and damage claims.",
      steps: [
        { title: "FC Dispatches", desc: "Use the Dispatch Dashboard to group multiple replenishment requests into a Batch Dispatch." },
        { title: "Returns & Damage", desc: "Process incoming Amazon/B2B returns. Log damaged goods with video proof in Damage Claims." },
        { title: "BKR Replenishment", desc: "Review low-stock alerts from retail arms and generate inter-company Delivery Challans." },
        { title: "Defective Inventory", desc: "Quarantine failed items so they cannot be accidentally sold." }
      ],
      actionText: "Open Logistics Dashboard",
      actionRoute: ROUTES.LOGISTICS_DISPATCH_DASHBOARD
    },
    accounting: {
      title: "Accounting & Export Sync",
      description: "Export operational data to your primary accounting software (Tally).",
      steps: [
        { title: "Master Sync", desc: "Ensure your Chart of Accounts (Ledgers, Taxes, Banks) map correctly between the ERP and Tally." },
        { title: "Export Center", desc: "Select the date range and export type (Sales, Credit Notes, Journals)." },
        { title: "Download Files", desc: "Click Export to download the CSV formatted exactly for Tally import." },
        { title: "Business Reports", desc: "Use the Reports tab to download granular breakdown of Sales, Inventory, and Dispatches." }
      ],
      actionText: "Open Export Center",
      actionRoute: ROUTES.ACCOUNTING_EXPORT_CENTER
    },
    uploads: {
      title: "Data Uploads & Templates",
      description: "Download sample CSV files to see how your data should be formatted before bulk importing.",
      steps: [
        { title: "Product Master", desc: "Required Headers: sku, name, tax_rate, base_price. Optional: description, category, brand, hsn_code, mrp." },
        { title: "Inventory Balance", desc: "Required Headers: sku, warehouse_name, quantity." },
        { title: "Formatting Rules", desc: "Always save files as UTF-8 CSV. Do not include extra spaces in headers. Do not use special characters in SKUs." },
        { title: "Upload Errors", desc: "If an upload fails, check for missing required fields, zero quantity, or duplicate SKUs in the same file." }
      ],
      actionText: "View Products",
      actionRoute: ROUTES.PRODUCTS
    }
  };

  const FAQS = [
    { q: "How do I reprint an old invoice?", a: "Go to 'Sales History', find the specific transaction using the date filter or search, and click the 'View/Print' button." },
    { q: "What if a customer returns an item?", a: "Navigate to 'Sales Returns'. You can process a return against a specific invoice, which will automatically put the item back into your warehouse inventory." },
    { q: "How do I fix incorrect GST rates on an invoice?", a: "GST rates are pulled from the Product Master. If it's wrong, an Admin needs to update the product in the 'Products' section before you generate the bill." },
    { q: "Why can't I generate a Service Invoice?", a: "You can only generate a Service Invoice if the associated Job Card is marked as 'COMPLETED'." },
  ];

  const handleDownloadSample = (type) => {
    let csvContent = "data:text/csv;charset=utf-8,";
    let filename = "";
    if (type === 'products') {
      csvContent += "sku,name,description,category,brand,hsn_code,tax_rate,base_price,mrp\n";
      csvContent += "PROD-001,Demo Power Drill,12V Drill,Power Tools,Bosch,8467,18,1500,2000\n";
      filename = "sample_products.csv";
    } else if (type === 'inventory') {
      csvContent += "sku,warehouse_name,quantity\n";
      csvContent += "PROD-001,Main Warehouse,50\n";
      filename = "sample_inventory.csv";
    }
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const activeContent = MANUAL_CONTENT[activeRole];

  // Simple filter for steps based on search
  const filteredSteps = activeContent.steps.filter(step => 
    step.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    step.desc.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className={styles.container}>
      {/* Hero Banner */}
      <div className={styles.heroBanner}>
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>How can we help you today?</h1>
          <p className={styles.heroSubtitle}>Search our knowledge base or select your role to get started.</p>
          
          <div className={styles.searchBar}>
            <FiSearch className={styles.searchIcon} size={20} />
            <input 
              type="text" 
              placeholder="Search guides, workflows, or FAQs..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </div>
        </div>
      </div>

      <div className={styles.mainLayout}>
        <div className={styles.sidebar}>
          <h3 className={styles.sectionTitle}>Role-Based Guides</h3>
          <nav className={styles.roleNav}>
            {ROLES.map(role => (
              <button 
                key={role.id}
                className={`${styles.roleButton} ${activeRole === role.id ? styles.activeRole : ''}`}
                onClick={() => {
                  setActiveRole(role.id);
                  setSearchQuery('');
                }}
              >
                <div className={`${styles.iconWrapper} ${activeRole === role.id ? styles.activeIcon : ''}`}>
                  <role.icon size={18} />
                </div>
                <span>{role.name}</span>
              </button>
            ))}
          </nav>

          <div className={styles.supportCard}>
            <div className={styles.supportIcon}><FiHelpCircle size={24} /></div>
            <h4>Need More Help?</h4>
            <p>If you're stuck, our team is available to assist you.</p>
            <div className={styles.contactLinks}>
              <a href="mailto:monuahlawatxyx@gmail.com" className={styles.contactLink}><FiMail /> Email Support</a>
              <a href="tel:+919817169403" className={styles.contactLink}><FiPhoneCall /> Call Team</a>
            </div>
          </div>
        </div>

        <div className={styles.contentArea}>
          {/* Workstation Guide Card */}
          <div className={styles.guideCard}>
            <div className={styles.guideHeader}>
              <div>
                <h2>{activeContent.title}</h2>
                <p>{activeContent.description}</p>
              </div>
              <button 
                className={styles.primaryActionButton} 
                onClick={() => navigate(activeContent.actionRoute)}
              >
                {activeContent.actionText}
                <FiArrowRight size={18} />
              </button>
            </div>
            
            {activeRole === 'uploads' && (
              <div className={styles.sampleDownloads}>
                <h3 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Download Sample Files</h3>
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                  <button 
                    onClick={() => handleDownloadSample('products')}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)', fontWeight: '500' }}
                  >
                    <FiDownload /> Product Master CSV
                  </button>
                  <button 
                    onClick={() => handleDownloadSample('inventory')}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)', fontWeight: '500' }}
                  >
                    <FiDownload /> Inventory Balance CSV
                  </button>
                </div>
              </div>
            )}

            <div className={styles.stepsGrid}>
              {filteredSteps.length > 0 ? filteredSteps.map((step, index) => (
                <div key={index} className={styles.stepBox}>
                  <div className={styles.stepNumber}>{index + 1}</div>
                  <div className={styles.stepContent}>
                    <h4>{step.title}</h4>
                    <p>{step.desc}</p>
                  </div>
                </div>
              )) : (
                <div className={styles.noResults}>
                  <FiMessageSquare size={32} className={styles.noResultIcon} />
                  <p>No steps found matching "{searchQuery}".</p>
                </div>
              )}
            </div>
          </div>

          {/* FAQ Section */}
          <div className={styles.faqSection}>
            <h3 className={styles.sectionTitle}>Frequently Asked Questions</h3>
            <div className={styles.faqList}>
              {FAQS.filter(faq => faq.q.toLowerCase().includes(searchQuery.toLowerCase()) || faq.a.toLowerCase().includes(searchQuery.toLowerCase())).map((faq, idx) => (
                <div 
                  key={idx} 
                  className={`${styles.faqItem} ${openFaq === idx ? styles.faqItemOpen : ''}`}
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                >
                  <div className={styles.faqHeader}>
                    <h4>{faq.q}</h4>
                    {openFaq === idx ? <FiChevronUp /> : <FiChevronDown />}
                  </div>
                  {openFaq === idx && (
                    <div className={styles.faqAnswer}>
                      <p>{faq.a}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default UserManualPage;

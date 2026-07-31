from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.db import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("CompanyUser", back_populates="company")
    products = relationship("Product", back_populates="company")
    warehouses = relationship("Warehouse", back_populates="company")
    inventories = relationship("Inventory", back_populates="company")
    movements = relationship("InventoryMovement", back_populates="company")
    amazon_sync_logs = relationship("AmazonSyncLog", back_populates="company")
    reports = relationship("ReportHistory", back_populates="company")
    alerts = relationship("Alert", back_populates="company")
    job_logs = relationship("JobExecutionLog", back_populates="company")

class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    role = Column(String, default="Admin")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="company_access")
    company = relationship("Company", back_populates="users")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="Viewer") # Admin or Viewer
    created_at = Column(DateTime, default=datetime.utcnow)

    company_access = relationship("CompanyUser", back_populates="user")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    sku = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String)
    brand = Column(String)
    item_rate = Column(Float, default=0.0)
    min_stock_level = Column(Integer, default=0)
    status = Column(String, default="Active")
    hsn = Column(String)
    hsn_code = Column(String)
    default_gst_rate = Column(Float, nullable=True) # None triggers 0% warning in POS
    barcode = Column(String)
    unit = Column(String)
    
    __table_args__ = (UniqueConstraint('company_id', 'sku', name='uix_company_sku'),)

    company = relationship("Company", back_populates="products")
    
    inventories = relationship("Inventory", back_populates="product")
    movements = relationship("InventoryMovement", back_populates="product")

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, index=True)
    status = Column(String, default="Active")
    address = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint('company_id', 'code', name='uix_company_warehouse_code'),)

    company = relationship("Company", back_populates="warehouses")
    inventories = relationship("Inventory", back_populates="warehouse")
    movements = relationship("InventoryMovement", back_populates="warehouse")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    current_qty = Column(Integer, default=0)
    reserved_qty = Column(Integer, default=0)
    available_qty = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('company_id', 'product_id', 'warehouse_id', name='uix_company_prod_wh'),)

    company = relationship("Company", back_populates="inventories")
    product = relationship("Product", back_populates="inventories")
    warehouse = relationship("Warehouse", back_populates="inventories")

    @property
    def product_sku(self):
        return self.product.sku if self.product else None

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    qty_before = Column(Integer, nullable=False)
    qty_changed = Column(Integer, nullable=False)
    qty_after = Column(Integer, nullable=False)
    source = Column(String, nullable=False) # Upload, Amazon, Manual, Transfer
    reference_id = Column(String) # e.g. INV-12345
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_payload = Column(JSON, default=dict)

    company = relationship("Company", back_populates="movements")
    product = relationship("Product", back_populates="movements")
    warehouse = relationship("Warehouse", back_populates="movements")

    @property
    def product_sku(self):
        return self.product.sku if self.product else None

class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=0)

class AmazonSyncLog(Base):
    __tablename__ = "amazon_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    order_id = Column(String, index=True, nullable=True)
    sync_start_time = Column(DateTime, default=datetime.utcnow)
    sync_end_time = Column(DateTime, nullable=True)
    status = Column(String, default="IN_PROGRESS")
    api_response_status = Column(String, nullable=True)
    orders_processed = Column(Integer, default=0)
    movements_created = Column(Integer, default=0)
    skipped_duplicates = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    unknown_skus = Column(String, nullable=True) # JSON string array
    next_token = Column(String, nullable=True)
    errors = Column(String, nullable=True)
    
    __table_args__ = (UniqueConstraint('company_id', 'order_id', name='uix_company_order_id'),)

    company = relationship("Company", back_populates="amazon_sync_logs")

class ReportHistory(Base):
    __tablename__ = "reports_history"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_type = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String, nullable=False)
    download_link = Column(String, nullable=False)

    company = relationship("Company", back_populates="reports")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    alert_type = Column(String, nullable=False) # LowStock, NegativeStock, SyncError
    message = Column(String, nullable=False)
    is_resolved = Column(Boolean, default=False)

    company = relationship("Company", back_populates="alerts")

class JobExecutionLog(Base):
    __tablename__ = "job_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    job_name = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    status = Column(String, nullable=False) # e.g. "Running", "Success", "Failed"
    error_message = Column(String, nullable=True)

    company = relationship("Company", back_populates="job_logs")

class CompanySettings(Base):
    """
    Per-company settings used by Billing/POS without changing the core Company table.
    Stores:
    - optional company profile fields (to snapshot into invoices)
    - tally integration configuration (optional)
    """
    __tablename__ = "company_settings"

    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)

    # Company profile (source for snapshot)
    legal_name = Column(String, nullable=True)
    gstin = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    state = Column(String, nullable=True)
    state_code = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    bank_details = Column(JSON, nullable=True)  # {bank_name, account_no, ifsc, branch, upi, ...}

    # Billing default text
    declaration = Column(Text, nullable=True)
    terms_of_delivery_default = Column(String, nullable=True)

    # Tally Integration (optional)
    tally_enabled = Column(Boolean, default=False)
    tally_endpoint_url = Column(String, nullable=True)
    tally_payload_format = Column(String, default="XML")  # XML | JSON

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")


class InvoiceSequence(Base):
    """
    Per-company invoice numbering sequence.
    Example invoice numbers:
      BKR/26-27/012
      JSPL/26-27/103
    """
    __tablename__ = "invoice_sequences"
    __table_args__ = (UniqueConstraint('company_id', 'fiscal_year', name='uix_company_fy_sequence'),)

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    fiscal_year = Column(String, nullable=False)  # e.g. "26-27"
    last_number = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")


class AuditLog(Base):
    """
    Lightweight audit logging for important operational events.
    (e.g. invoice created, tally sync started/success/failed)
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    entity_type = Column(String, nullable=False)  # "Sale", etc.
    entity_id = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)   # "INVOICE_CREATED", "TALLY_SYNC_STARTED", ...
    message = Column(Text, nullable=True)
    metadata_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (UniqueConstraint('company_id', 'bill_number', name='uix_company_bill_number'),)

    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String, index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    customer_name = Column(String, nullable=True)
    customer_mobile = Column(String, nullable=True)
    sale_date = Column(DateTime, default=datetime.utcnow)
    total_taxable_amount = Column(Float, default=0.0)
    total_tax = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    payment_method = Column(String, nullable=True) # Cash, UPI, Card, Bank Transfer, Cheque, Credit
    payment_reference = Column(String, nullable=True)  # UPI txn ref, cheque no, etc.
    payment_date = Column(DateTime, nullable=True)
    status = Column(String, default="Completed") # Draft, Completed, Cancelled, Returned
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ------------------------------------------------------------------
    # Invoice/Billing Snapshot Fields (extend Sale for now; future-proofed
    # by keeping renderer/export services separate from persistence)
    # ------------------------------------------------------------------

    # Invoice identity
    invoice_number = Column(String, nullable=True, index=True)
    invoice_type = Column(String, default="B2C")  # B2C | B2B

    # Customer snapshot
    customer_gstin = Column(String, nullable=True)
    customer_address = Column(Text, nullable=True)
    customer_state = Column(String, nullable=True)
    customer_state_code = Column(String, nullable=True)
    place_of_supply = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)

    # Invoice information
    payment_terms = Column(String, nullable=True)
    delivery_note = Column(String, nullable=True)
    delivery_note_date = Column(DateTime, nullable=True)
    dispatch_document_number = Column(String, nullable=True)
    dispatch_through = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)
    lr_rr_number = Column(String, nullable=True)
    terms_of_delivery = Column(String, nullable=True)

    # Company snapshot (do NOT fetch from Company at print time)
    company_name_snapshot = Column(String, nullable=True)
    company_gstin_snapshot = Column(String, nullable=True)
    company_address_snapshot = Column(Text, nullable=True)
    company_state_snapshot = Column(String, nullable=True)
    company_state_code_snapshot = Column(String, nullable=True)
    company_email_snapshot = Column(String, nullable=True)
    company_phone_snapshot = Column(String, nullable=True)
    company_logo_url_snapshot = Column(String, nullable=True)
    company_bank_details_snapshot = Column(JSON, nullable=True)

    # Optional e-invoice fields (if needed later)
    einvoice_irn = Column(String, nullable=True)
    einvoice_ack_no = Column(String, nullable=True)
    einvoice_ack_date = Column(DateTime, nullable=True)
    einvoice_qr_code_data = Column(Text, nullable=True)

    # Tally sync metadata (B2B only, optional and configurable)
    tally_sync_status = Column(String, default="NOT_APPLICABLE")  # NOT_APPLICABLE|PENDING|PROCESSING|SUCCESS|FAILED|RETRYING|CANCELLED
    tally_sync_at = Column(DateTime, nullable=True)
    tally_reference = Column(String, nullable=True)
    tally_error_message = Column(Text, nullable=True)

    company = relationship("Company")
    creator = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    selling_price = Column(Float, nullable=False)
    gst_rate = Column(Float, default=0.0)
    taxable_amount = Column(Float, default=0.0)
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    igst = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    # Invoice line snapshot fields
    product_name = Column(String, nullable=True)
    hsn_sac = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    discount = Column(Float, default=0.0)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.db import Base

class AccountingConfiguration(Base):
    __tablename__ = "acc_configurations"

    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    default_sales_ledger = Column(String, nullable=True)
    default_purchase_ledger = Column(String, nullable=True)
    round_off_ledger = Column(String, nullable=True)
    discount_ledger = Column(String, nullable=True)
    freight_ledger = Column(String, nullable=True)
    default_godown = Column(String, nullable=True)
    default_voucher_type = Column(String, default="Sales")
    voucher_series = Column(String, nullable=True)
    min_tally_version = Column(String, nullable=True)
    xml_version = Column(String, default="1")
    export_format = Column(String, default="XML") # XML, JSON
    http_endpoint = Column(String, default="http://localhost:9000")
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")


class AccountingMapping(Base):
    __tablename__ = "acc_mappings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    mapping_type = Column(String, nullable=False) # Company, Ledger, Product
    erp_reference = Column(String, nullable=False) # e.g. "BKR", "CGST", "SKU-1"
    accounting_name = Column(String, nullable=False) # e.g. "B.K. Raman & Co.", "Output CGST 9%"
    aliases = Column(String, nullable=True) # Optional JSON string list
    
    __table_args__ = (UniqueConstraint('company_id', 'mapping_type', 'erp_reference', name='uix_acc_mapping'),)
    
    company = relationship("Company")


class AccountingExportBatch(Base):
    __tablename__ = "acc_export_batches"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    batch_type = Column(String, nullable=False) # e.g. Sales, Warehouse
    batch_subtype = Column(String, nullable=True) # e.g. B2C, B2B, Returns
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="Queued") # Queued, Generating, Generated, Downloaded, Awaiting Import, Imported
    file_path = Column(String, nullable=True) # Path to stored XML file on disk
    invoice_count = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    
    checksum_sha256 = Column(String, nullable=True)
    template_version = Column(String, nullable=True)
    erp_version = Column(String, default="1.0.0")

    company = relationship("Company")
    creator = relationship("User")
    logs = relationship("AccountingExportLog", back_populates="batch")


class AccountingExportLog(Base):
    __tablename__ = "acc_export_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("acc_export_batches.id"), nullable=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    
    # Draft, Ready, XML Generated, Downloaded, Imported, Verified, Completed, Failed, Needs Review
    status = Column(String, default="Ready")
    
    last_export_time = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    tally_response_status = Column(String, nullable=True) # 1 or 0
    tally_response_message = Column(Text, nullable=True)

    company = relationship("Company")
    batch = relationship("AccountingExportBatch", back_populates="logs")
    sale = relationship("Sale")


class MasterSyncLog(Base):
    __tablename__ = "acc_master_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    master_type = Column(String, nullable=False) # Customer, Product, Ledger, Godown
    entity_id = Column(String, nullable=False) # e.g. "CUST-1", "PROD-2"
    sync_status = Column(String, default="Pending") # Pending, Synced, Failed
    last_synced_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (UniqueConstraint('company_id', 'master_type', 'entity_id', name='uix_master_sync'),)

    company = relationship("Company")

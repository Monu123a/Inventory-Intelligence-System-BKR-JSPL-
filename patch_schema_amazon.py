import re

file_path = "backend/app/models/schema.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Add AmazonNetworkType and new classes
new_classes = """

class AmazonNetworkType(str, enum.Enum):
    MFN = "MFN"
    AFN = "AFN"

class AllocationStatus(str, enum.Enum):
    PENDING = "Pending"
    UNSHIPPED = "Unshipped"
    SHIPPED = "Shipped"
    CANCELLED = "Cancelled"
    RETURNED = "Returned"
    REFUNDED = "Refunded"

class AmazonLiveAllocation(Base):
    __tablename__ = "amazon_live_allocations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    order_id = Column(String, nullable=False, index=True)
    amazon_line_item_id = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    amazon_network_at_allocation = Column(Enum(AmazonNetworkType), nullable=True)
    allocated_qty = Column(Integer, default=0)
    reconciled_qty = Column(Integer, default=0)
    status = Column(Enum(AllocationStatus), default=AllocationStatus.PENDING)
    closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('order_id', 'sku', 'amazon_line_item_id', name='uix_amazon_order_sku_line'),
        Index('idx_order_sku_lineitem', 'order_id', 'sku', 'amazon_line_item_id'),
        Index('idx_unreconciled_allocations', 'reconciled_qty', 'allocated_qty'),
        Index('idx_updated_at', 'updated_at'),
        Index('idx_status', 'status')
    )

class AmazonOrderEventLog(Base):
    __tablename__ = "amazon_order_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    allocation_id = Column(Integer, ForeignKey("amazon_live_allocations.id"), nullable=False)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class DLQType(str, enum.Enum):
    MATCH_FAILED = "MATCH_FAILED"
    RATE_LIMIT = "RATE_LIMIT"
    DATA_MISMATCH = "DATA_MISMATCH"
    API_FAILURE = "API_FAILURE"

class AmazonDLQ(Base):
    __tablename__ = "amazon_dlq"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    dlq_type = Column(Enum(DLQType), nullable=False)
    reference_id = Column(String, nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

"""
if "class AmazonLiveAllocation" not in content:
    content += new_classes

# 2. Update WarehouseExternalMapping
if "amazon_network = Column(Enum(AmazonNetworkType), nullable=True)" not in content:
    content = content.replace(
        "external_code = Column(String, nullable=False, index=True) # e.g. BOM1",
        "external_code = Column(String, nullable=False, index=True) # e.g. BOM1\n    amazon_network = Column(Enum(AmazonNetworkType), nullable=True)"
    )

# 3. Add amazon_sync_enabled
if "amazon_sync_enabled = Column(Boolean, default=False)" not in content:
    content = content.replace(
        "amazon_returns_sync_enabled = Column(Boolean, default=False)",
        "amazon_sync_enabled = Column(Boolean, default=False)\n    amazon_returns_sync_enabled = Column(Boolean, default=False)"
    )

with open(file_path, "w") as f:
    f.write(content)


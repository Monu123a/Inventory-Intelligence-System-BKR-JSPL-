from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class JobCardItemBase(BaseModel):
    item_name: str
    product_sku: Optional[str] = None
    source: str = "manual"
    source_invoice_item_id: Optional[int] = None
    qty: float = Field(default=1.0, gt=0, le=1000)
    rate: float = Field(default=0.0, ge=0)
    amount: float = Field(default=0.0, ge=0)

class JobCardItemCreate(JobCardItemBase):
    pass

class JobCardItemResponse(JobCardItemBase):
    id: int
    job_card_id: int

    class Config:
        orm_mode = True

class JobCardBase(BaseModel):
    service_record_id: int
    workshop_id: int
    assigned_to: Optional[int] = None
    status: str = "OPEN"

class JobCardCreate(JobCardBase):
    items: List[JobCardItemCreate] = []

class JobCardDirectCreate(BaseModel):
    # Customer Details
    customer_name: str = Field(..., min_length=1)
    customer_mobile: Optional[str] = None
    
    # Source / Invoice reference
    source_type: str = "manual"
    source_invoice_id: Optional[str] = None
    
    # Service / Machine Details
    product_name: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1)
    complaint: str = Field(..., min_length=5)
    service_type: str = "Repair"
    service_location: str = "Workshop"
    
    # Job Card Assignments
    workshop_id: int
    assigned_to: Optional[int] = None
    
    # Items
    items: List[JobCardItemCreate] = Field(..., min_length=1)

class JobCardUpdateStatus(BaseModel):
    status: str

class JobCardResponse(JobCardBase):
    id: int
    company_id: int
    job_card_number: str
    date: datetime
    is_verified: Optional[bool] = False
    
    # Flat properties pulled from underlying ServiceRecord
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    address: Optional[str] = None
    product_name: Optional[str] = None
    brand: Optional[str] = None
    complaint: Optional[str] = None
    
    items: List[JobCardItemResponse] = []

    class Config:
        orm_mode = True

class ServiceInvoiceItemBase(BaseModel):
    description: str
    product_sku: Optional[str] = None
    hsn: Optional[str] = None
    gst_rate: float = Field(default=0.0, ge=0)
    qty: float = Field(default=1.0, gt=0)
    rate: float = Field(default=0.0, ge=0)
    amount: float = Field(default=0.0, ge=0)

class ServiceInvoiceItemCreate(ServiceInvoiceItemBase):
    pass

class ServiceInvoiceItemResponse(ServiceInvoiceItemBase):
    id: int
    invoice_id: int

    class Config:
        orm_mode = True

class ServiceInvoiceBase(BaseModel):
    job_card_id: int
    total_amount: float = Field(default=0.0, ge=0)
    cgst_amount: float = Field(default=0.0, ge=0)
    sgst_amount: float = Field(default=0.0, ge=0)
    grand_total: float = Field(default=0.0, ge=0)

class ServiceInvoiceCreate(ServiceInvoiceBase):
    items: List[ServiceInvoiceItemCreate]

class ServiceInvoiceResponse(ServiceInvoiceBase):
    id: int
    company_id: int
    invoice_number: str
    date: datetime
    items: List[ServiceInvoiceItemResponse] = []
    job_card: Optional[JobCardResponse] = None

    class Config:
        orm_mode = True

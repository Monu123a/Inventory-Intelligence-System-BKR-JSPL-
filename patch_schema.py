import os

file_path = "backend/app/models/schema.py"
with open(file_path, "r") as f:
    content = f.read()

# Add Customer class if not exists
if "class Customer(" not in content:
    customer_class = """
class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    gstin = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    state = Column(String, nullable=True)
    state_code = Column(String, nullable=True)
    place_of_supply = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company")

"""
    # Insert before class Vendor
    content = content.replace("class Vendor(Base):", customer_class + "class Vendor(Base):")
    with open(file_path, "w") as f:
        f.write(content)

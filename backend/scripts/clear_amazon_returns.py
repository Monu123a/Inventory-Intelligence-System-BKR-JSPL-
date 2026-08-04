import sys
import os

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.db import SessionLocal
from app.models.schema import AmazonReturn, DefectiveInventory

def clear_returns_data():
    db = SessionLocal()
    
    # First delete DefectiveInventory because it has foreign keys referencing AmazonReturn
    deleted_defective = db.query(DefectiveInventory).delete()
    print(f"Deleted {deleted_defective} defective inventory records.")

    # Next delete all AmazonReturns
    deleted_returns = db.query(AmazonReturn).delete()
    print(f"Deleted {deleted_returns} amazon returns.")

    db.commit()
    print("Successfully cleared all Amazon Returns and Defective Inventory data.")

if __name__ == "__main__":
    clear_returns_data()

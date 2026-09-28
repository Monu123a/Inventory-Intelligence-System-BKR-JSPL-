from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.schema import AmazonLiveAllocation, Inventory

class StockReservationService:
    @staticmethod
    def get_available_stock(db: Session, company_id: int, product_id: int, warehouse_id: int = None) -> int:
        """
        Calculates Available Stock = Core Stock - (allocated_qty - reconciled_qty)
        Can be scoped to a specific warehouse or company-wide.
        """
        # Get Core Stock
        core_query = db.query(func.sum(Inventory.current_qty)).filter(
            Inventory.company_id == company_id,
            Inventory.product_id == product_id
        )
        if warehouse_id:
            core_query = core_query.filter(Inventory.warehouse_id == warehouse_id)
            
        core_stock = core_query.scalar() or 0
        
        # We need the product SKU to query AmazonLiveAllocation
        from app.models.schema import Product
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return 0
            
        # Get Unreconciled Allocations
        allocation_query = db.query(
            func.sum(AmazonLiveAllocation.allocated_qty - AmazonLiveAllocation.reconciled_qty)
        ).filter(
            AmazonLiveAllocation.company_id == company_id,
            AmazonLiveAllocation.sku == product.sku,
            AmazonLiveAllocation.closed == False,
            AmazonLiveAllocation.allocated_qty > AmazonLiveAllocation.reconciled_qty
        )
        if warehouse_id:
            allocation_query = allocation_query.filter(AmazonLiveAllocation.warehouse_id == warehouse_id)
            
        unreconciled_allocations = allocation_query.scalar() or 0
        
        return core_stock - unreconciled_allocations


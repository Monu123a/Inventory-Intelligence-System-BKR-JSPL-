from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.schema import (
    Inventory, Product, SaleItem, Sale, ReplenishmentRun, 
    ReplenishmentRecommendation, AmazonSyncLog
)

class ReplenishmentService:
    @staticmethod
    def analyze_inventory(db: Session, company_id: int):
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Today's demand logic: query Sale and SaleItem for today
        demand_query = (
            db.query(SaleItem.product_id, func.sum(SaleItem.quantity).label('total_demand'))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(Sale.company_id == company_id)
            .filter(Sale.sale_date >= today_start)
            .group_by(SaleItem.product_id)
            .all()
        )
        
        demand_map = {row.product_id: row.total_demand for row in demand_query}
        
        # Aggregate inventory across all warehouses for the company
        inventories = (
            db.query(
                Inventory.product_id,
                func.sum(Inventory.current_qty).label('current_qty'),
                func.sum(Inventory.reserved_qty).label('reserved_qty'),
            )
            .filter(Inventory.company_id == company_id)
            .group_by(Inventory.product_id)
            .all()
        )
        
        # Pre-fetch products to get safety_stock
        product_ids = [inv.product_id for inv in inventories]
        products = db.query(Product).filter(Product.id.in_(product_ids)).all() if product_ids else []
        product_map = {p.id: p for p in products}
        
        run = ReplenishmentRun(
            company_id=company_id,
            status="Success",
            run_date=datetime.utcnow()
        )
        db.add(run)
        db.flush()
        
        recommendations_created = 0
        for inv in inventories:
            product = product_map.get(inv.product_id)
            if not product:
                continue
                
            # Handle potential None values from SUM
            current_qty = inv.current_qty or 0
            reserved_qty = inv.reserved_qty or 0
            
            available_stock = current_qty - reserved_qty
            today_demand = demand_map.get(inv.product_id, 0)
            safety_stock = product.safety_stock or 0
            
            required_qty = today_demand + safety_stock - available_stock
            
            if required_qty > 0:
                rec = ReplenishmentRecommendation(
                    run_id=run.id,
                    product_id=inv.product_id,
                    current_stock=current_qty,
                    reserved_stock=reserved_qty,
                    available_stock=available_stock,
                    today_demand=today_demand,
                    safety_stock=safety_stock,
                    recommended_qty=required_qty,
                    status="Pending"
                )
                db.add(rec)
                recommendations_created += 1
                
        if recommendations_created == 0:
            run.reason = "No replenishment required."
            
        db.commit()
        return run

    @staticmethod
    def verify_amazon_sync(db: Session, company_id: int) -> bool:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        log = (
            db.query(AmazonSyncLog)
            .filter(AmazonSyncLog.company_id == company_id)
            .filter(AmazonSyncLog.sync_start_time >= today_start)
            .filter(AmazonSyncLog.status.in_(["SUCCESS", "COMPLETED"]))
            .filter(AmazonSyncLog.orders_processed >= 0)
            .first()
        )
        return log is not None

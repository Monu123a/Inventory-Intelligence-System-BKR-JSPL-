from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.schema import Inventory, InventoryMovement, Warehouse
from app.models.db import SessionLocal
import logging

logger = logging.getLogger(__name__)

def generate_45_day_return_recommendations():
    """
    Scans FC inventory to find products that have been sitting for > 45 days
    without any movement (sales or transfers), and flags them for return recommendations.
    Does NOT automatically move stock.
    """
    db: Session = SessionLocal()
    try:
        # Find all FC Warehouses (warehouses that have a hub_id)
        fc_warehouses = db.query(Warehouse).filter(Warehouse.hub_id.isnot(None)).all()
        fc_warehouse_ids = [w.id for w in fc_warehouses]
        
        if not fc_warehouse_ids:
            return
            
        # Get inventory with available stock in FCs
        stale_threshold = datetime.utcnow() - timedelta(days=45)
        
        recommendations = []
        inventories = db.query(Inventory).filter(
            Inventory.warehouse_id.in_(fc_warehouse_ids),
            Inventory.available_qty > 0
        ).all()
        
        for inv in inventories:
            # Check the most recent movement for this product at this FC
            last_movement = db.query(InventoryMovement).filter(
                InventoryMovement.warehouse_id == inv.warehouse_id,
                InventoryMovement.product_id == inv.product_id
            ).order_by(InventoryMovement.created_at.desc()).first()
            
            if last_movement and last_movement.created_at < stale_threshold:
                # It's been >45 days since the last movement
                recommendations.append({
                    "warehouse_id": inv.warehouse_id,
                    "product_id": inv.product_id,
                    "quantity": inv.available_qty,
                    "last_movement_date": last_movement.created_at.isoformat(),
                    "days_stale": (datetime.utcnow() - last_movement.created_at).days
                })
                
        # In a real implementation, these recommendations would be saved to a database table
        # like `FCReturnRecommendation` to be served by the API.
        # For this phase, we can log them or return them.
        # Since we don't have a specific model requested for recommendations, 
        # we can provide an API endpoint that computes this on the fly,
        # or we could create a cache table.
        # Given the requirements: "flag them for the 45-Day Return Recommendations dashboard",
        # returning them directly from a service function that the API calls might be sufficient,
        # or writing to a lightweight JSON file/Redis if caching is needed.
        # The user just said "The scheduler should scan FC inventory daily... Generate a recommendation."
        
        logger.info(f"Found {len(recommendations)} 45-day return recommendations.")
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating 45-day return recommendations: {e}")
    finally:
        db.close()

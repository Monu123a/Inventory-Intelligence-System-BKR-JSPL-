from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import cast, Date
from app.models.schema import ServiceReminder, Sale, SaleItem

class ServiceReminderService:
    @staticmethod
    def generate_reminders(db: Session, company_id: int):
        # 6 months is approx 180 days. Or we can use dateutil.relativedelta.
        # But standard timedelta(days=182) is common. Let's use 182 days as 6 months.
        target_date = (datetime.utcnow() - timedelta(days=182)).date()
        
        # We find sales that are exactly on or before the target date,
        # but the user requested: sale_date <= today - 6 months
        # So we query all sales where sale_date.date() <= target_date
        
        # We only want to generate reminders for products that don't already have one
        # to prevent duplicates.
        
        # Fetch eligible sales
        sales = db.query(Sale).filter(
            Sale.company_id == company_id,
            cast(Sale.sale_date, Date) <= target_date,
            Sale.status == "Completed"
        ).all()
        
        count = 0
        for sale in sales:
            # Get items
            items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
            for item in items:
                # Check if reminder exists
                existing = db.query(ServiceReminder).filter(
                    ServiceReminder.sale_id == sale.id,
                    ServiceReminder.product_id == item.product_id
                ).first()
                
                if not existing:
                    reminder = ServiceReminder(
                        company_id=company_id,
                        sale_id=sale.id,
                        product_id=item.product_id,
                        customer_id=sale.id, # Using Sale ID as surrogate customer ID for now
                        customer_name_snapshot=sale.customer_name,
                        customer_mobile_snapshot=sale.customer_mobile,
                        sale_date=sale.sale_date,
                        reminder_date=sale.sale_date + timedelta(days=182),
                        status="Pending"
                    )
                    db.add(reminder)
                    count += 1
        
        if count > 0:
            db.commit()
            
        return count
        
    @staticmethod
    def update_status(db: Session, company_id: int, reminder_id: int, status: str) -> ServiceReminder:
        reminder = db.query(ServiceReminder).filter(
            ServiceReminder.id == reminder_id,
            ServiceReminder.company_id == company_id
        ).first()
        
        if not reminder:
            raise ValueError("Reminder not found")
            
        if status not in ["Pending", "Contacted", "Completed", "Dismissed"]:
            raise ValueError("Invalid status")
            
        reminder.status = status
        db.flush()
        return reminder

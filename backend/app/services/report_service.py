import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.schema import Inventory, Product, Warehouse, ReportHistory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

class ReportService:
    @staticmethod
    def _save_and_log_report(db: Session, df: pd.DataFrame, report_type: str, format: str, company_id: int) -> ReportHistory:
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type.replace(' ', '_')}_{timestamp_str}.{format}"
        filepath = os.path.join(REPORTS_DIR, filename)
        
        if format == "csv":
            df.to_csv(filepath, index=False)
        else:
            df.to_excel(filepath, index=False)
            
        download_link = f"/api/reports/download/{filename}"
        
        report = ReportHistory(
            company_id=company_id,
            report_type=report_type,
            file_path=filepath,
            download_link=download_link
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def generate_low_stock(db: Session, company_id: int, format: str = "xlsx") -> ReportHistory:
        query = db.query(
            Product.sku.label("product_sku"),
            Product.name,
            Warehouse.name.label("warehouse"),
            Inventory.current_qty,
            Product.min_stock_level,
            Product.item_rate
        ).join(Product, Inventory.product_id == Product.id)\
         .join(Warehouse, Inventory.warehouse_id == Warehouse.id)\
         .filter(Inventory.company_id == company_id, Inventory.current_qty >= 0, Inventory.current_qty < Product.min_stock_level, Product.min_stock_level > 0)
         
        df = pd.read_sql(query.statement, db.bind)
        if df.empty:
            raise ValueError("No low stock items found.")
            
        return ReportService._save_and_log_report(db, df, "Low Stock Report", format, company_id)

    @staticmethod
    def generate_negative_stock(db: Session, company_id: int, format: str = "xlsx") -> ReportHistory:
        query = db.query(
            Product.sku.label("product_sku"),
            Product.name,
            Warehouse.name.label("warehouse"),
            Inventory.current_qty
        ).join(Product, Inventory.product_id == Product.id)\
         .join(Warehouse, Inventory.warehouse_id == Warehouse.id)\
         .filter(Inventory.company_id == company_id, Inventory.current_qty < 0)
         
        df = pd.read_sql(query.statement, db.bind)
        if df.empty:
            raise ValueError("No negative stock items found.")
            
        return ReportService._save_and_log_report(db, df, "Negative Stock Report", format, company_id)

    @staticmethod
    def generate_replenishment(db: Session, company_id: int, format: str = "xlsx") -> ReportHistory:
        query = db.query(
            Product.sku,
            Product.name,
            func.sum(Inventory.current_qty).label("total_current_qty"),
            Product.min_stock_level,
            Product.item_rate
        ).join(Inventory, Product.id == Inventory.product_id)\
         .filter(Product.company_id == company_id, Product.min_stock_level > 0)\
         .group_by(Product.sku, Product.name, Product.min_stock_level, Product.item_rate)\
         .having(func.sum(Inventory.current_qty) < Product.min_stock_level)
         
        df = pd.read_sql(query.statement, db.bind)
        if df.empty:
            raise ValueError("No replenishment needed.")
            
        df["Required Quantity"] = df["min_stock_level"] - df["total_current_qty"]
        
        return ReportService._save_and_log_report(db, df, "Daily Replenishment Report", format, company_id)

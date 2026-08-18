import pandas as pd
from typing import List, Dict, Any

class InventoryAdapter:
    """
    Adapter to parse uploaded inventory Excel/CSV files.
    """
    
    @staticmethod
    def parse_inventory_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Takes an uploaded Excel/CSV file and returns normalized JSON data.
        
        Expected output format:
        [
            {"sku": "ABC-123", "quantity": 50},
            ...
        ]
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
                
            results = []
            
            # Find the SKU and Quantity columns dynamically
            sku_col = next((col for col in df.columns if str(col).lower().strip() in ["sku", "item code", "product", "item_code", "item sku"]), None)
            qty_col = next((col for col in df.columns if str(col).lower().strip() in ["quantity", "qty", "stock", "count", "current_qty"]), None)
            
            if not sku_col or not qty_col:
                raise ValueError(f"Could not find SKU or Quantity columns in the uploaded file. Columns found: {df.columns.tolist()}. Please ensure your file has columns like 'SKU' and 'Quantity'.")

            for _, row in df.iterrows():
                sku_val = str(row[sku_col]).strip()[:6]
                qty_val = row[qty_col]
                    
                if sku_val and isinstance(sku_val, str) and sku_val.lower() != "nan" and sku_val != "":
                    results.append({
                        "sku": sku_val,
                        "quantity": qty_val
                    })
                    
            return results
            
        except Exception as e:
            raise Exception(f"Failed to parse inventory file: {str(e)}")

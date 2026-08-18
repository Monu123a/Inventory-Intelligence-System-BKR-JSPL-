import pandas as pd
from typing import List
from app.repositories.config_repository import ConfigRepository

class ConfigurationGenerator:
    """
    Configuration Generator Engine (formerly Inference Engine).
    Infers the mapping between Amazon raw input, internal schema, and Logic ERP output.
    """
    def __init__(self, config_repo: ConfigRepository):
        self.config_repo = config_repo

    def infer_from_samples(self, raw_data_path: str, transformed_data_path: str) -> None:
        """
        Parses the raw data and transformed data to infer mappings and rules.
        """
        raw_df = pd.read_excel(raw_data_path, nrows=0)
        transformed_df = pd.read_excel(transformed_data_path, nrows=0)
        
        raw_columns = raw_df.columns.tolist()
        transformed_columns = transformed_df.columns.tolist()

        mapping_data = {
            "amazon_to_internal": {},
            "internal_to_logic_erp": {}
        }
        
        # 1. Infer Amazon Input columns mapped to our known internal schema names
        def find_col(possible_names: List[str]) -> str:
            for name in possible_names:
                if name in raw_columns:
                    return name
            return "NOT_FOUND"

        mapping_data["amazon_to_internal"] = {
            find_col(["Invoice Number", "invoice-id"]): "invoice_number",
            find_col(["Sku", "sku"]): "sku",
            find_col(["Transaction Type", "transaction-type"]): "transaction_type",
            find_col(["Ship To State", "ship-state"]): "state",
            find_col(["Customer Bill To Gstid", "buyer-tax-registration-id"]): "buyer_gst",
            "Principal Amount": "principal_amount",
            "Cgst Tax": "cgst_tax",
            "Sgst Tax": "sgst_tax",
            "Igst Tax": "igst_tax",
            "Shipping Amount": "shipping_amount"
        }

        # 2. Logic ERP Output columns are inferred exactly from transformed report
        # The target schema is essentially the columns of the transformed report.
        # We save this as the expected output column list.
        mapping_data["logic_erp_output_columns"] = transformed_columns
        
        self.config_repo.save_mapping(mapping_data)

        # 3. Generate Default Rules Configuration
        rules_data = {
            "TransactionFilter": {
                "enabled": True,
                "allowed": ["Shipment"]
            },
            "InvoiceFilter": {
                "enabled": True,
                "prefixes": ["VSHB", "IN"]
            },
            "SkuTrim": {
                "enabled": True,
                "length": 6
            },
            "LocationFilter": {
                "enabled": True,
                "allowed_states": ["Chandigarh"]
            },
            "DefaultInjector": {
                "enabled": True,
                "defaults": {
                    "MEM SHIP": "Standard",
                    "TAX REGION": "Local"
                }
            },
            "AccountCodeMapper": {
                "enabled": True,
                "gst_lookup_source": "GSTIN_FIRST_TWO_DIGITS" 
            }
        }
        self.config_repo.save_rules(rules_data)
        
        # 4. Generate Lookups Config
        lookups_data = {
            "account_lookup": "STATE CODE AND ACCOUNT CODE.xlsx"
        }
        self.config_repo.save_lookups_config(lookups_data)

        print("Configuration Generation completed from sample files!")

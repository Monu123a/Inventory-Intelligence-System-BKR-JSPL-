import logging
import pandas as pd
from app.plugins.base import BasePlugin
from app.models.context import ExecutionContext, LogLevel

logger = logging.getLogger(__name__)

class SkuMasterMapperPlugin(BasePlugin):
    NAME = "SkuMasterMapper"
    VERSION = "1.0"
    DESCRIPTION = "Looks up fields like GST Slab from the SKU Master using SKU as the primary key."

    def execute(self, context: ExecutionContext) -> None:
        df = context.current_data
        if df is None or df.empty:
            return

        cfg = context.rules.get(self.NAME, {})
        amazon_key = cfg.get("amazon_key", "Sku")
        master_key = cfg.get("master_key", "SKU")
        fields_to_map = cfg.get("fields_to_map", {})

        if not fields_to_map:
            return

        # Initialize mapped columns with None
        for mapped_col in fields_to_map.values():
            if mapped_col not in df.columns:
                df[mapped_col] = None

        if amazon_key not in df.columns:
            context.add_warning(LogLevel.WARNING, f"Column '{amazon_key}' not found in data – skipping SkuMasterMapper.")
            context.current_data = df
            return

        # Load the SKU Master lookup table
        master_df = context.lookups.get("sku_master")
        if master_df is None or master_df.empty:
            context.add_warning(LogLevel.ERROR, "SKU Master table not loaded – cannot map SKUs.")
            context.current_data = df
            return

        if master_key not in master_df.columns:
            context.add_warning(LogLevel.ERROR, f"Master key '{master_key}' not found in SKU Master.")
            context.current_data = df
            return

        # Clean up master keys
        master_df[master_key] = master_df[master_key].astype(str).str.strip().str.upper()

        # Check for duplicates in SKU master
        duplicates = master_df[master_df.duplicated(subset=[master_key], keep=False)]
        if not duplicates.empty:
            dup_skus = duplicates[master_key].unique().tolist()
            context.add_warning(
                LogLevel.WARNING,
                f"Duplicate SKUs found in SKU Master: {dup_skus[:10]}" + ("..." if len(dup_skus) > 10 else "")
            )
            logger.warning(f"Duplicate SKUs in Master: {dup_skus}")
            # Keep only the first occurrence to avoid merge explosion
            master_df = master_df.drop_duplicates(subset=[master_key], keep='first')

        # Create dictionaries for fast lookup
        lookup_dicts = {}
        for source_field, dest_field in fields_to_map.items():
            if source_field in master_df.columns:
                lookup_dicts[dest_field] = dict(zip(master_df[master_key], master_df[source_field]))
            else:
                context.add_warning(LogLevel.WARNING, f"Source field '{source_field}' not found in SKU Master.")
                lookup_dicts[dest_field] = {}

        missing_count = 0
        missing_gst_count = 0

        # Perform the mapping
        for idx, row in df.iterrows():
            sku_val = str(row.get(amazon_key, "")).strip().upper()
            
            if not sku_val or sku_val == "NAN":
                continue

            # Check if SKU exists in ANY of the lookups (we use the first one as representative)
            first_dest_field = list(fields_to_map.values())[0] if fields_to_map else None
            
            if first_dest_field and sku_val not in lookup_dicts[first_dest_field]:
                missing_count += 1
                context.add_warning(
                    LogLevel.WARNING,
                    f"SKU '{sku_val}' not found in SKU Master.",
                    row_index=int(idx),
                    column=amazon_key,
                )
            
            for dest_field, l_dict in lookup_dicts.items():
                val = l_dict.get(sku_val, "")
                if pd.isna(val):
                    val = ""
                df.at[idx, dest_field] = val
                
                # Check for missing GST specifically, as requested
                if 'gst' in str(dest_field).lower() and not str(val).strip():
                    missing_gst_count += 1
                    context.add_warning(
                        LogLevel.WARNING,
                        f"Missing GST value for SKU '{sku_val}' in Master.",
                        row_index=int(idx),
                        column=dest_field,
                    )

        context.current_data = df
        
        if missing_count > 0:
            context.add_warning(LogLevel.INFO, f"SkuMasterMapper: {missing_count} SKUs were missing from the Master.")
        if missing_gst_count > 0:
            context.add_warning(LogLevel.INFO, f"SkuMasterMapper: {missing_gst_count} SKUs had missing GST values.")
            
        logger.info(f"SkuMasterMapper completed. Missing SKUs: {missing_count}")

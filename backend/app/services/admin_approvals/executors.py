import json
import math
from app.services.admin_approvals.registry import Executor, ExecutorRegistry
from app.models.schema import Product

class SnapshotMismatchError(Exception):
    def __init__(self, diff: dict):
        self.diff = diff
        super().__init__("Snapshot mismatch")

class UpdateProductPriceExecutor(Executor):
    name = "UPDATE_PRODUCT_PRICE"
    allowed_request_roles = ["Admin", "Manager", "Operator"]
    allowed_approve_roles = ["Admin"]

    def validate(self, payload: dict) -> None:
        if "product_id" not in payload:
            raise ValueError("product_id is required")
        if "new_price" not in payload:
            raise ValueError("new_price is required")
        if not isinstance(payload["new_price"], (int, float)):
            raise ValueError("new_price must be numeric")
        if "company_id" not in payload:
            raise ValueError("company_id is required for tenant isolation")

    def lock_entities(self, db, payload: dict) -> None:
        # Multi-entity lock ordering (Future-proofing for bulk arrays)
        product_ids = [payload["product_id"]] if isinstance(payload["product_id"], int) else payload["product_id"]
        product_ids = sorted(product_ids)
        
        targets = db.query(Product).filter(Product.id.in_(product_ids)).order_by(Product.id.asc()).with_for_update().all()
        if len(targets) != len(product_ids):
            raise ValueError(f"Some products not found during lock")
            
        # Enforce Tenant Boundary (Cross-company protection)
        for t in targets:
            if t.company_id != payload["company_id"]:
                raise PermissionError(f"Tenant boundary violation: Product {t.id} belongs to different company.")

    def before_snapshot(self, db, payload: dict) -> dict:
        product = db.query(Product).filter(Product.id == payload["product_id"]).first()
        if not product:
            raise ValueError(f"Product {payload['product_id']} not found")
        return {
            "product_id": product.id,
            "sku": product.sku,
            "price": float(product.item_rate)
        }

    def compare_snapshot(self, before: dict, current: dict) -> None:
        diff = {}
        if before.get("sku") != current.get("sku"):
            diff["sku"] = {"old": before.get("sku"), "current": current.get("sku")}
            
        old_price = before.get("price", 0.0)
        curr_price = current.get("price", 0.0)
        if not math.isclose(old_price, curr_price, abs_tol=1e-5):
            diff["price"] = {"old": old_price, "current": curr_price}

        if diff:
            raise SnapshotMismatchError(diff=diff)

    def dry_run(self, db, payload: dict) -> dict:
        snapshot = self.before_snapshot(db, payload)
        return {
            "changes": [
                {
                    "entity": "Product",
                    "id": payload["product_id"],
                    "field": "item_rate",
                    "old_value": snapshot["price"],
                    "new_value": payload["new_price"]
                }
            ],
            "estimated_impact": "Sync execution, 1 row updated."
        }

    def execute(self, db, payload: dict, idempotency_key: str) -> dict:
        product = db.query(Product).filter(Product.id == payload["product_id"]).first()
        old_price = float(product.item_rate)
        product.item_rate = payload["new_price"]
        db.flush()
        return {
            "changed": True,
            "old_price": old_price,
            "new_price": payload["new_price"],
            "product_id": product.id,
            "sku": product.sku,
            "price": float(product.item_rate) # Used for 'after_snapshot'
        }

    def reverse_payload(self, payload: dict, before_snapshot: dict) -> dict:
        return {
            "product_id": payload["product_id"],
            "new_price": before_snapshot["price"],
            "company_id": payload["company_id"]
        }

ExecutorRegistry.register(UpdateProductPriceExecutor())


class UpdateProductExecutor(Executor):
    name = "UPDATE_PRODUCT"
    allowed_request_roles = ["Admin", "Manager", "Operator"]
    allowed_approve_roles = ["Admin"]

    def validate(self, payload: dict) -> None:
        if "id" not in payload and "product_id" not in payload and "sku" not in payload:
            raise ValueError("id, product_id, or sku is required")
        if "company_id" not in payload:
            raise ValueError("company_id is required for tenant isolation")

    def _get_product(self, db, payload: dict):
        if "id" in payload:
            return db.query(Product).filter(Product.id == payload["id"], Product.company_id == payload["company_id"]).first()
        elif "product_id" in payload:
            return db.query(Product).filter(Product.id == payload["product_id"], Product.company_id == payload["company_id"]).first()
        elif "sku" in payload:
            return db.query(Product).filter(Product.sku == payload["sku"], Product.company_id == payload["company_id"]).first()
        return None

    def lock_entities(self, db, payload: dict) -> None:
        product = self._get_product(db, payload)
        if not product:
            raise ValueError("Product not found")
        
        # Lock
        t = db.query(Product).filter(Product.id == product.id).with_for_update().first()
        if not t:
            raise ValueError("Product not found during lock")

    def before_snapshot(self, db, payload: dict) -> dict:
        product = self._get_product(db, payload)
        if not product:
            raise ValueError("Product not found")
        # Dump all product fields to a dict (simple fields)
        return {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "item_rate": float(product.item_rate) if product.item_rate else 0.0,
            "default_gst_rate": float(product.default_gst_rate) if product.default_gst_rate else 0.0,
            "status": product.status,
            "min_stock_level": product.min_stock_level
        }

    def compare_snapshot(self, before: dict, current: dict) -> None:
        diff = {}
        for k, v in before.items():
            curr_v = current.get(k)
            # handle float comparison for item_rate and gst
            if isinstance(v, float) and isinstance(curr_v, (float, int)):
                if not math.isclose(v, float(curr_v), abs_tol=1e-5):
                    diff[k] = {"old": v, "current": curr_v}
            elif v != curr_v:
                diff[k] = {"old": v, "current": curr_v}
                
        if diff:
            raise SnapshotMismatchError(diff=diff)

    def dry_run(self, db, payload: dict) -> dict:
        snapshot = self.before_snapshot(db, payload)
        changes = []
        for key, new_val in payload.items():
            if key in snapshot and snapshot[key] != new_val:
                changes.append({
                    "entity": "Product",
                    "id": snapshot["id"],
                    "field": key,
                    "old_value": snapshot[key],
                    "new_value": new_val
                })
                
        return {
            "changes": changes,
            "estimated_impact": "Sync execution, 1 row updated."
        }

    def execute(self, db, payload: dict, idempotency_key: str) -> dict:
        product = self._get_product(db, payload)
        
        # apply changes
        exclude_keys = {"id", "company_id", "admin_password"}
        for key, value in payload.items():
            if key not in exclude_keys and hasattr(product, key):
                setattr(product, key, value)
                
        db.flush()
        
        return {
            "changed": True,
            "product_id": product.id,
            "sku": product.sku,
            # After snapshot
            "after": self.before_snapshot(db, payload)
        }

    def reverse_payload(self, payload: dict, before_snapshot: dict) -> dict:
        revert = {"company_id": payload["company_id"], "id": before_snapshot["id"]}
        # restore old values that were touched by the payload
        for k in payload.keys():
            if k in before_snapshot:
                revert[k] = before_snapshot[k]
        return revert

ExecutorRegistry.register(UpdateProductExecutor())

"""create missing accounting tables

Revision ID: 6b6988e5f36a
Revises: f24b9a346c65
Create Date: 2026-08-19 14:44:52.624961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b6988e5f36a'
down_revision: Union[str, Sequence[str], None] = 'f24b9a346c65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    from app.models.db import Base
    from app.models.schema import Company, User, Warehouse, Product, Inventory, InventoryMovement, AmazonSyncLog, Alert, JobExecutionLog, Sale, SaleItem, SalesReturn, DeliveryChallan, FCDispatch, FCReturn, ServiceRecord
    from app.models.accounting_schema import AccountingExportBatch, AccountingSystemConfig, AccountingMapping, AccountingMasterSyncLog
    Base.metadata.create_all(bind=conn)

def downgrade() -> None:
    pass

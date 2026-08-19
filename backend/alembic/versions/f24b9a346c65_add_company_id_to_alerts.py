"""add company_id to alerts

Revision ID: f24b9a346c65
Revises: 91c96a4deca8
Create Date: 2026-08-19 14:26:39.956113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f24b9a346c65'
down_revision: Union[str, Sequence[str], None] = '91c96a4deca8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

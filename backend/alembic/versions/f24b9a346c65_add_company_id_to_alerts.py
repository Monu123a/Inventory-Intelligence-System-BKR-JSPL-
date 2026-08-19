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
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(sa.text("""
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE alerts ADD COLUMN company_id INTEGER REFERENCES companies(id);
            EXCEPTION
                WHEN duplicate_column THEN RAISE NOTICE 'column company_id already exists';
            END;
        END $$;
        """))
    else:
        with op.batch_alter_table('alerts', schema=None) as batch_op:
            batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=True))

def downgrade() -> None:
    pass

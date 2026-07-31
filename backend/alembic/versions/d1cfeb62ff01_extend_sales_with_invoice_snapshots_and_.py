"""extend sales with invoice snapshots and tally metadata

Revision ID: d1cfeb62ff01
Revises: cba99dc7c9e1
Create Date: 2026-07-31 11:41:56.301966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1cfeb62ff01'
down_revision: Union[str, Sequence[str], None] = 'cba99dc7c9e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "company_settings",
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("legal_name", sa.String(), nullable=True),
        sa.Column("gstin", sa.String(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("state_code", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("bank_details", sa.JSON(), nullable=True),
        sa.Column("declaration", sa.Text(), nullable=True),
        sa.Column("terms_of_delivery_default", sa.String(), nullable=True),
        sa.Column("tally_enabled", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("tally_endpoint_url", sa.String(), nullable=True),
        sa.Column("tally_payload_format", sa.String(), server_default="XML", nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "invoice_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("fiscal_year", sa.String(), nullable=False),
        sa.Column("last_number", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table("invoice_sequences") as batch_op:
        batch_op.create_unique_constraint("uix_company_fy_sequence", ["company_id", "fiscal_year"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # sales table extensions
    op.add_column("sales", sa.Column("invoice_number", sa.String(), nullable=True))
    op.create_index("ix_sales_invoice_number", "sales", ["invoice_number"])
    op.add_column("sales", sa.Column("invoice_type", sa.String(), server_default="B2C", nullable=False))

    op.add_column("sales", sa.Column("customer_gstin", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("customer_address", sa.Text(), nullable=True))
    op.add_column("sales", sa.Column("customer_state", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("customer_state_code", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("place_of_supply", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("customer_email", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("customer_phone", sa.String(), nullable=True))

    op.add_column("sales", sa.Column("payment_terms", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("delivery_note", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("delivery_note_date", sa.DateTime(), nullable=True))
    op.add_column("sales", sa.Column("dispatch_document_number", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("dispatch_through", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("destination", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("vehicle_number", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("lr_rr_number", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("terms_of_delivery", sa.String(), nullable=True))

    op.add_column("sales", sa.Column("company_name_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_gstin_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_address_snapshot", sa.Text(), nullable=True))
    op.add_column("sales", sa.Column("company_state_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_state_code_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_email_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_phone_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_logo_url_snapshot", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("company_bank_details_snapshot", sa.JSON(), nullable=True))

    op.add_column("sales", sa.Column("einvoice_irn", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("einvoice_ack_no", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("einvoice_ack_date", sa.DateTime(), nullable=True))
    op.add_column("sales", sa.Column("einvoice_qr_code_data", sa.Text(), nullable=True))

    op.add_column("sales", sa.Column("tally_sync_status", sa.String(), server_default="NOT_APPLICABLE", nullable=False))
    op.add_column("sales", sa.Column("tally_sync_at", sa.DateTime(), nullable=True))
    op.add_column("sales", sa.Column("tally_reference", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("tally_error_message", sa.Text(), nullable=True))

    op.add_column("sales", sa.Column("payment_reference", sa.String(), nullable=True))
    op.add_column("sales", sa.Column("payment_date", sa.DateTime(), nullable=True))

    # sale_items extensions
    op.add_column("sale_items", sa.Column("igst", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("sale_items", sa.Column("product_name", sa.String(), nullable=True))
    op.add_column("sale_items", sa.Column("hsn_sac", sa.String(), nullable=True))
    op.add_column("sale_items", sa.Column("unit", sa.String(), nullable=True))
    op.add_column("sale_items", sa.Column("discount", sa.Float(), server_default="0.0", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    # sale_items
    op.drop_column("sale_items", "discount")
    op.drop_column("sale_items", "unit")
    op.drop_column("sale_items", "hsn_sac")
    op.drop_column("sale_items", "product_name")
    op.drop_column("sale_items", "igst")

    # sales
    op.drop_column("sales", "payment_date")
    op.drop_column("sales", "payment_reference")
    op.drop_column("sales", "tally_error_message")
    op.drop_column("sales", "tally_reference")
    op.drop_column("sales", "tally_sync_at")
    op.drop_column("sales", "tally_sync_status")

    op.drop_column("sales", "einvoice_qr_code_data")
    op.drop_column("sales", "einvoice_ack_date")
    op.drop_column("sales", "einvoice_ack_no")
    op.drop_column("sales", "einvoice_irn")

    op.drop_column("sales", "company_bank_details_snapshot")
    op.drop_column("sales", "company_logo_url_snapshot")
    op.drop_column("sales", "company_phone_snapshot")
    op.drop_column("sales", "company_email_snapshot")
    op.drop_column("sales", "company_state_code_snapshot")
    op.drop_column("sales", "company_state_snapshot")
    op.drop_column("sales", "company_address_snapshot")
    op.drop_column("sales", "company_gstin_snapshot")
    op.drop_column("sales", "company_name_snapshot")

    op.drop_column("sales", "terms_of_delivery")
    op.drop_column("sales", "lr_rr_number")
    op.drop_column("sales", "vehicle_number")
    op.drop_column("sales", "destination")
    op.drop_column("sales", "dispatch_through")
    op.drop_column("sales", "dispatch_document_number")
    op.drop_column("sales", "delivery_note_date")
    op.drop_column("sales", "delivery_note")
    op.drop_column("sales", "payment_terms")

    op.drop_column("sales", "customer_phone")
    op.drop_column("sales", "customer_email")
    op.drop_column("sales", "place_of_supply")
    op.drop_column("sales", "customer_state_code")
    op.drop_column("sales", "customer_state")
    op.drop_column("sales", "customer_address")
    op.drop_column("sales", "customer_gstin")

    op.drop_column("sales", "invoice_type")
    op.drop_index("ix_sales_invoice_number", table_name="sales")
    op.drop_column("sales", "invoice_number")

    # new tables
    op.drop_table("audit_logs")
    op.drop_table("invoice_sequences")
    op.drop_table("company_settings")

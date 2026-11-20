"""Dự phòng credit Firecrawl ước tính dùng chung theo ngày UTC.

Revision ID: 0008_credit_reservations
Revises: 0007_brand_create_key
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_credit_reservations"
down_revision = "0007_brand_create_key"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "firecrawl_credit_reservations",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("unit_estimate", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.CheckConstraint("daily_limit >= 0 AND unit_estimate > 0 AND reserved >= 0 AND reserved <= daily_limit",
                           name="ck_firecrawl_credit_reservation"),
    )


def downgrade():
    op.drop_table("firecrawl_credit_reservations")

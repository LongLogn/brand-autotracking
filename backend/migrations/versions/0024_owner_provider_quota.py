"""Dự phòng hạn mức nhà cung cấp theo chủ sở hữu và ngày UTC.

Revision ID: 0024_owner_provider_quota
Revises: 0023_alert_email_delivery
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_owner_provider_quota"
down_revision = "0023_alert_email_delivery"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "owner_provider_quotas",
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.CheckConstraint("reserved > 0", name="ck_owner_provider_quota_reserved"),
    )


def downgrade():
    op.drop_table("owner_provider_quotas")

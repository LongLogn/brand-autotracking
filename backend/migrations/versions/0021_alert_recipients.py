"""Địa chỉ nhận cảnh báo theo nhãn hàng.

Revision ID: 0021_alert_recipients
Revises: 0020_run_alerts
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_alert_recipients"
down_revision = "0020_run_alerts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brands", sa.Column("alert_emails", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    op.drop_column("brands", "alert_emails")

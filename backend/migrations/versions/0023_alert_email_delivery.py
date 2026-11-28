"""Theo dõi việc gửi email cho cảnh báo demo.

Revision ID: 0023_alert_email_delivery
Revises: 0022_demo_alert_evaluation
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_alert_email_delivery"
down_revision = "0022_demo_alert_evaluation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("alerts", sa.Column("email_status", sa.String(16), nullable=True))
    op.add_column("alerts", sa.Column("email_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("alerts", sa.Column("email_due_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_alerts_email_due", "alerts", ["email_status", "email_due_at"])


def downgrade():
    op.drop_index("ix_alerts_email_due", table_name="alerts")
    op.drop_column("alerts", "email_due_at")
    op.drop_column("alerts", "email_attempts")
    op.drop_column("alerts", "email_status")

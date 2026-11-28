"""Lưu kết quả đánh giá theo phiên demo.

Revision ID: 0022_demo_alert_evaluation
Revises: 0021_alert_recipients
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_demo_alert_evaluation"
down_revision = "0021_alert_recipients"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tracking_runs", sa.Column("alert_evaluation", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("tracking_runs", "alert_evaluation")

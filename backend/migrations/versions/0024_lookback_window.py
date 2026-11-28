"""Khung thời gian thu thập (số ngày gần nhất) và thông báo thiếu bài trong khung.

Revision ID: 0024_lookback_window
Revises: 0023_analysis_queue
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_lookback_window"
down_revision = "0023_analysis_queue"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tracking_configs", sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="90"))
    op.create_check_constraint("ck_tracking_lookback_days", "tracking_configs", "lookback_days BETWEEN 1 AND 365")
    op.add_column("tracking_attempts", sa.Column("notice", sa.String(64)))


def downgrade():
    op.drop_column("tracking_attempts", "notice")
    op.drop_constraint("ck_tracking_lookback_days", "tracking_configs", type_="check")
    op.drop_column("tracking_configs", "lookback_days")

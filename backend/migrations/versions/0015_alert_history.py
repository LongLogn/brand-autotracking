"""Lưu lịch sử cảnh báo duy nhất theo quy tắc và cửa sổ.

Revision ID: 0015_alert_history
Revises: 0014_observation_evidence
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_alert_history"
down_revision = "0014_observation_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(16), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_negative", sa.Integer(), nullable=False),
        sa.Column("current_negative", sa.Integer(), nullable=False),
        sa.Column("growth_percent", sa.Integer(), nullable=False),
        sa.Column("minimum_current", sa.Integer(), nullable=False),
        sa.Column("absolute_threshold", sa.Integer()),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id", "content_type"], ["alert_rules.brand_id", "alert_rules.content_type"], name="fk_alert_rule"),
        sa.UniqueConstraint("brand_id", "content_type", "window_end", name="uq_alert_window"),
    )
    op.create_index("ix_alerts_brand_id", "alerts", ["brand_id"])


def downgrade():
    op.drop_index("ix_alerts_brand_id", table_name="alerts")
    op.drop_table("alerts")

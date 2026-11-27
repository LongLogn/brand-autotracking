"""Lưu quy tắc cảnh báo theo nhãn hàng và loại nội dung.

Revision ID: 0011_alert_rules
Revises: 0010_tracking_lease
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_alert_rules"
down_revision = "0010_tracking_lease"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alert_rules",
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), primary_key=True),
        sa.Column("content_type", sa.String(16), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("growth_percent", sa.Integer(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("minimum_current", sa.Integer(), nullable=False),
        sa.Column("absolute_threshold", sa.Integer()),
        sa.CheckConstraint("content_type IN ('post', 'comment')", name="ck_alert_rule_content_type"),
        sa.CheckConstraint("growth_percent BETWEEN 0 AND 1000", name="ck_alert_rule_growth"),
        sa.CheckConstraint("window_days BETWEEN 1 AND 90", name="ck_alert_rule_window"),
        sa.CheckConstraint("minimum_current >= 1", name="ck_alert_rule_minimum"),
        sa.CheckConstraint("absolute_threshold IS NULL OR absolute_threshold >= 1", name="ck_alert_rule_absolute"),
    )


def downgrade():
    op.drop_table("alert_rules")

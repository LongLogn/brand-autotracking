"""Cảnh báo theo lần thu thập demo và trạng thái gửi thông báo.

Revision ID: 0020_run_alerts
Revises: 0019_bedrock_rate
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_run_alerts"
down_revision = "0019_bedrock_rate"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("alerts", sa.Column("mode", sa.String(16), nullable=False, server_default="window"))
    op.add_column("alerts", sa.Column("run_id", sa.Uuid(), sa.ForeignKey("tracking_runs.id", name="fk_alert_run"), nullable=True))
    op.add_column("alerts", sa.Column("previous_total", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("current_total", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_alert_run", "alerts", ["run_id", "content_type"])
    op.create_check_constraint("ck_alert_mode", "alerts", "mode IN ('window', 'run')")
    op.create_check_constraint("ck_alert_run_fields", "alerts",
                               "(mode = 'window' AND run_id IS NULL) OR "
                               "(mode = 'run' AND run_id IS NOT NULL AND previous_total > 0 AND current_total > 0)")


def downgrade():
    op.execute("DELETE FROM alerts WHERE mode = 'run'")
    op.drop_constraint("ck_alert_run_fields", "alerts", type_="check")
    op.drop_constraint("ck_alert_mode", "alerts", type_="check")
    op.drop_constraint("uq_alert_run", "alerts", type_="unique")
    op.drop_column("alerts", "notified_at")
    op.drop_column("alerts", "current_total")
    op.drop_column("alerts", "previous_total")
    op.drop_column("alerts", "run_id")
    op.drop_column("alerts", "mode")

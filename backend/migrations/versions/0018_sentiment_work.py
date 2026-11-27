"""Hàng đợi bền vững cho phân loại cảm xúc theo phiên.

Revision ID: 0018_sentiment_work
Revises: 0017_sentiment_version
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_sentiment_work"
down_revision = "0017_sentiment_version"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sentiment_work",
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("tracking_runs.id"), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'running', 'complete', 'failed')", name="ck_sentiment_work_status"),
        sa.CheckConstraint("failures >= 0 AND failures <= 3", name="ck_sentiment_work_failures"),
        sa.CheckConstraint("(status = 'running' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
                           "(status <> 'running' AND lease_token IS NULL AND lease_expires_at IS NULL)", name="ck_sentiment_work_lease"),
    )
    # Chỉ tạo công việc cho các phiên đã chốt; tính năng xử lý vẫn mặc định tắt.
    op.execute("""INSERT INTO sentiment_work (run_id, status, failures, next_attempt_at, updated_at)
                  SELECT id, 'pending', 0, clock_timestamp(), clock_timestamp()
                  FROM tracking_runs WHERE status IN ('success', 'partial', 'failed')""")


def downgrade():
    op.drop_table("sentiment_work")

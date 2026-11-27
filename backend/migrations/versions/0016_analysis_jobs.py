"""Lưu yêu cầu và kết quả phân tích có dẫn chứng.

Revision ID: 0016_analysis_jobs
Revises: 0015_alert_history
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_analysis_jobs"
down_revision = "0015_alert_history"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("request_key", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("sample_count", sa.Integer()),
        sa.Column("sample_truncated", sa.Boolean()),
        sa.Column("has_undated_comments", sa.Boolean()),
        sa.Column("evidence", sa.JSON()),
        sa.Column("findings", sa.JSON()),
        sa.Column("error_code", sa.String(40)),
        sa.CheckConstraint("status IN ('running', 'success', 'failed')", name="ck_analysis_status"),
        sa.UniqueConstraint("brand_id", "request_key", name="uq_analysis_brand_request"),
    )
    op.create_index("ix_analysis_jobs_brand_id", "analysis_jobs", ["brand_id"])


def downgrade():
    op.drop_index("ix_analysis_jobs_brand_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")

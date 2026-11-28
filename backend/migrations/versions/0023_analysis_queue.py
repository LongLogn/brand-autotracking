"""Hàng đợi phân tích AI: trạng thái queued, thời điểm thử lại và số lần thử.

Revision ID: 0023_analysis_queue
Revises: 0022_bedrock_rate_60
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_analysis_queue"
down_revision = "0022_bedrock_rate_60"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analysis_jobs", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("analysis_jobs", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("analysis_jobs", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.drop_constraint("ck_analysis_status", "analysis_jobs", type_="check")
    op.create_check_constraint("ck_analysis_status", "analysis_jobs", "status IN ('queued', 'running', 'success', 'failed')")
    op.create_index("ix_analysis_jobs_queue", "analysis_jobs", ["status", "next_attempt_at"],
                    postgresql_where=sa.text("status = 'queued'"))


def downgrade():
    op.drop_index("ix_analysis_jobs_queue", table_name="analysis_jobs")
    # Yêu cầu còn chờ không còn được xử lý khi hạ cấp; đánh dấu thất bại cho ràng buộc cũ.
    op.execute("UPDATE analysis_jobs SET status = 'failed', error_code = 'queue_timeout', finished_at = now() "
               "WHERE status = 'queued'")
    op.drop_constraint("ck_analysis_status", "analysis_jobs", type_="check")
    op.create_check_constraint("ck_analysis_status", "analysis_jobs", "status IN ('running', 'success', 'failed')")
    op.drop_column("analysis_jobs", "attempts")
    op.drop_column("analysis_jobs", "next_attempt_at")
    op.drop_column("analysis_jobs", "started_at")

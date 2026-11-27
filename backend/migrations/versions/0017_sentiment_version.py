"""Lưu phiên bản thuật toán phân loại để vô hiệu kết quả cũ.

Revision ID: 0017_sentiment_version
Revises: 0016_analysis_jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_sentiment_version"
down_revision = "0016_analysis_jobs"
branch_labels = None
depends_on = None


def upgrade():
    # Kết quả cũ thiếu phiên bản được giữ null, không gán phiên bản mới.
    op.add_column("sentiment_results", sa.Column("classifier_version", sa.String(32)))


def downgrade():
    op.drop_column("sentiment_results", "classifier_version")

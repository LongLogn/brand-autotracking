"""Lưu thời điểm và hash nội dung được quan sát cho từng phiên.

Revision ID: 0014_observation_evidence
Revises: 0013_bedrock_call_budget
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_observation_evidence"
down_revision = "0013_bedrock_call_budget"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("run_post_matches", "run_comment_matches"):
        op.add_column(table, sa.Column("observed_at", sa.DateTime(timezone=True)))
        op.add_column(table, sa.Column("content_hash", sa.String(64)))


def downgrade():
    for table in ("run_comment_matches", "run_post_matches"):
        op.drop_column(table, "content_hash")
        op.drop_column(table, "observed_at")

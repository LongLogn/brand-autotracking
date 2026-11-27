"""Dự phòng số lần gọi Bedrock theo ngày UTC.

Revision ID: 0013_bedrock_call_budget
Revises: 0012_sentiment_results
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_bedrock_call_budget"
down_revision = "0012_sentiment_results"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bedrock_call_reservations",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.CheckConstraint("daily_limit >= 0 AND reserved >= 0 AND reserved <= daily_limit",
                           name="ck_bedrock_call_reservation"),
    )


def downgrade():
    op.drop_table("bedrock_call_reservations")

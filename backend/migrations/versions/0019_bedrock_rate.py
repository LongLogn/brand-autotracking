"""Giới hạn burst lời gọi Bedrock theo phút UTC.

Revision ID: 0019_bedrock_rate
Revises: 0018_sentiment_work
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_bedrock_rate"
down_revision = "0018_sentiment_work"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bedrock_minute_reservations",
        sa.Column("minute", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.CheckConstraint("reserved >= 0 AND reserved <= 10", name="ck_bedrock_minute_reservation"),
    )


def downgrade():
    op.drop_table("bedrock_minute_reservations")

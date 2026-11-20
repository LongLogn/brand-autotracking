"""Thêm lease có fencing cho worker tracking.

Revision ID: 0010_tracking_lease
Revises: 0009_tracking_outbox
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_tracking_lease"
down_revision = "0009_tracking_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tracking_runs", sa.Column("lease_token", sa.Uuid(), nullable=True))
    op.add_column("tracking_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("tracking_runs", "lease_expires_at")
    op.drop_column("tracking_runs", "lease_token")

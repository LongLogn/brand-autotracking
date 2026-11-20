"""Tạo outbox bền vững cho phiên tracking đang chờ.

Revision ID: 0009_tracking_outbox
Revises: 0008_credit_reservations
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_tracking_outbox"
down_revision = "0008_credit_reservations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tracking_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("tracking_runs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("publish_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(100)),
        sa.UniqueConstraint("run_id", name="uq_tracking_outbox_run"),
    )
    # PostgreSQL có gen_random_uuid(); xếp các phiên còn chờ từ schema cũ.
    op.execute("""INSERT INTO tracking_outbox (id, run_id, created_at, publish_attempts)
                  SELECT gen_random_uuid(), id, now(), 0 FROM tracking_runs WHERE status = 'queued'""")


def downgrade():
    op.drop_table("tracking_outbox")

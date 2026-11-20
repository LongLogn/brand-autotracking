"""Phân biệt thời điểm tạo yêu cầu và thời điểm worker bắt đầu."""
from alembic import op
import sqlalchemy as sa

revision = "0005_queue_time"
down_revision = "0004_run_error"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tracking_runs", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE tracking_runs SET queued_at = started_at")
    op.alter_column("tracking_runs", "queued_at", nullable=False)
    op.alter_column("tracking_runs", "started_at", existing_type=sa.DateTime(timezone=True), nullable=True)


def downgrade():
    op.execute("UPDATE tracking_runs SET started_at = queued_at WHERE started_at IS NULL")
    op.alter_column("tracking_runs", "started_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.drop_column("tracking_runs", "queued_at")

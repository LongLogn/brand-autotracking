"""Lưu lý do kết thúc bất thường cho phiên."""
from alembic import op
import sqlalchemy as sa

revision = "0004_run_error"
down_revision = "0003_attempt_matches"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tracking_runs", sa.Column("error_code", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("tracking_runs", "error_code")

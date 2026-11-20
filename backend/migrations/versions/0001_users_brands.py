"""Khởi tạo tài khoản và nhãn hàng tối thiểu."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("cognito_sub", sa.String(255), nullable=False, unique=True))
    op.create_table("brands", sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("name", sa.String(200), nullable=False))
    op.create_index("ix_brands_owner_id", "brands", ["owner_id"])


def downgrade():
    op.drop_index("ix_brands_owner_id", table_name="brands")
    op.drop_table("brands")
    op.drop_table("users")

"""Cho phép thử lại yêu cầu tạo nhãn hàng theo tài khoản.

Revision ID: 0007_brand_create_key
Revises: 0006_comment_parent
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_brand_create_key"
down_revision = "0006_comment_parent"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brands", sa.Column("create_request_key", sa.Uuid(), nullable=True))
    op.add_column("brands", sa.Column("create_request_name", sa.String(200), nullable=True))
    op.create_unique_constraint("uq_brand_owner_create_key", "brands", ["owner_id", "create_request_key"])


def downgrade():
    op.drop_constraint("uq_brand_owner_create_key", "brands", type_="unique")
    op.drop_column("brands", "create_request_name")
    op.drop_column("brands", "create_request_key")

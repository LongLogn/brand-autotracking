"""Ràng buộc bình luận trong phiên phải có bài cha trong cùng phiên.

Revision ID: 0006_comment_parent
Revises: 0005_queue_time
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_comment_parent"
down_revision = "0005_queue_time"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("run_comment_matches", sa.Column("post_id", sa.Uuid(), nullable=True))
    op.execute("UPDATE run_comment_matches AS m SET post_id = c.post_id FROM comments AS c WHERE c.id = m.comment_id")
    op.alter_column("run_comment_matches", "post_id", nullable=False)
    op.create_unique_constraint("uq_comment_id_post_brand", "comments", ["id", "post_id", "brand_id"])
    op.create_unique_constraint("uq_run_post_brand", "run_post_matches", ["run_id", "post_id", "brand_id"])
    op.create_foreign_key("fk_run_comment_parent", "run_comment_matches", "comments",
                          ["comment_id", "post_id", "brand_id"], ["id", "post_id", "brand_id"])
    op.create_foreign_key("fk_run_comment_run_post", "run_comment_matches", "run_post_matches",
                          ["run_id", "post_id", "brand_id"], ["run_id", "post_id", "brand_id"])


def downgrade():
    op.drop_constraint("fk_run_comment_run_post", "run_comment_matches", type_="foreignkey")
    op.drop_constraint("fk_run_comment_parent", "run_comment_matches", type_="foreignkey")
    op.drop_constraint("uq_run_post_brand", "run_post_matches", type_="unique")
    op.drop_constraint("uq_comment_id_post_brand", "comments", type_="unique")
    op.drop_column("run_comment_matches", "post_id")

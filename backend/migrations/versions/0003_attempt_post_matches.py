"""Giữ liên hệ bài viết với từng lượt từ khóa trong phiên."""
from alembic import op
import sqlalchemy as sa

revision = "0003_attempt_matches"
down_revision = "881aef6486a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_attempt_id_run", "tracking_attempts", ["id", "run_id"])
    op.create_table(
        "attempt_post_matches",
        sa.Column("attempt_id", sa.Uuid(), primary_key=True),
        sa.Column("post_id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id", "run_id"], ["tracking_attempts.id", "tracking_attempts.run_id"], name="fk_attempt_post_attempt_run"),
        sa.ForeignKeyConstraint(["run_id", "brand_id"], ["tracking_runs.id", "tracking_runs.brand_id"], name="fk_attempt_post_run_brand"),
        sa.ForeignKeyConstraint(["post_id", "brand_id"], ["posts.id", "posts.brand_id"], name="fk_attempt_post_post_brand"),
    )


def downgrade():
    op.drop_table("attempt_post_matches")
    op.drop_constraint("uq_attempt_id_run", "tracking_attempts", type_="unique")

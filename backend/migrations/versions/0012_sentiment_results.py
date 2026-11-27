"""Lưu phân loại cảm xúc theo nội dung và nhãn hàng.

Revision ID: 0012_sentiment_results
Revises: 0011_alert_rules
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_sentiment_results"
down_revision = "0011_alert_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sentiment_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("post_id", sa.Uuid()),
        sa.Column("comment_id", sa.Uuid()),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(16), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)", name="ck_sentiment_one_target"),
        sa.CheckConstraint("label IN ('positive', 'negative', 'neutral', 'unknown')", name="ck_sentiment_label"),
        sa.ForeignKeyConstraint(["post_id", "brand_id"], ["posts.id", "posts.brand_id"], name="fk_sentiment_post_brand"),
        sa.ForeignKeyConstraint(["comment_id", "brand_id"], ["comments.id", "comments.brand_id"], name="fk_sentiment_comment_brand"),
        sa.UniqueConstraint("post_id", name="uq_sentiment_post"),
        sa.UniqueConstraint("comment_id", name="uq_sentiment_comment"),
    )
    op.create_index("ix_sentiment_results_brand_id", "sentiment_results", ["brand_id"])


def downgrade():
    op.drop_index("ix_sentiment_results_brand_id", table_name="sentiment_results")
    op.drop_table("sentiment_results")

"""Nâng giới hạn lời gọi Bedrock theo phút từ 10 lên 60.

Revision ID: 0022_bedrock_rate_60
Revises: 0021_alert_recipients
"""
from alembic import op

revision = "0022_bedrock_rate_60"
down_revision = "0021_alert_recipients"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_bedrock_minute_reservation", "bedrock_minute_reservations", type_="check")
    op.create_check_constraint("ck_bedrock_minute_reservation", "bedrock_minute_reservations",
                               "reserved >= 0 AND reserved <= 60")


def downgrade():
    # Hạ về 10: cắt các phút đã vượt để ràng buộc cũ hợp lệ.
    op.execute("UPDATE bedrock_minute_reservations SET reserved = 10 WHERE reserved > 10")
    op.drop_constraint("ck_bedrock_minute_reservation", "bedrock_minute_reservations", type_="check")
    op.create_check_constraint("ck_bedrock_minute_reservation", "bedrock_minute_reservations",
                               "reserved >= 0 AND reserved <= 10")

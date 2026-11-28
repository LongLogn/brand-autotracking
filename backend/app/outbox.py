"""Phát sự kiện tracking sang SQS theo mô hình at-least-once."""
import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import TrackingOutbox, TrackingRun


def publish_pending(db_engine, sqs, queue_url, limit=20, max_attempts=10):
    """Giữ khóa outbox khi gửi; commit lỗi sau gửi có thể tạo thông điệp lặp."""
    if not queue_url or not 1 <= limit <= 100 or not 1 <= max_attempts <= 100:
        raise ValueError("Cần URL hàng đợi và giới hạn hợp lệ")
    with Session(db_engine) as db:
        ids = db.scalars(select(TrackingOutbox.id).join(TrackingRun, TrackingRun.id == TrackingOutbox.run_id)
                         .where(TrackingOutbox.published_at.is_(None), TrackingOutbox.publish_attempts < max_attempts,
                                TrackingRun.status == "queued")
                         .order_by(TrackingOutbox.created_at, TrackingOutbox.id).limit(limit)).all()
    published = failed = 0
    for event_id in ids:
        with Session(db_engine) as db, db.begin():
            row = db.scalar(select(TrackingOutbox).where(TrackingOutbox.id == event_id,
                            TrackingOutbox.published_at.is_(None), TrackingOutbox.publish_attempts < max_attempts)
                            .with_for_update(skip_locked=True))
            if row is None:
                continue
            run = db.get(TrackingRun, row.run_id)
            if run is None or run.status != "queued":
                continue
            row.publish_attempts += 1
            body = json.dumps({"event_id": str(row.id), "run_id": str(row.run_id)}, separators=(",", ":"))
            try:
                sqs.send_message(QueueUrl=queue_url, MessageBody=body)
            except Exception:
                # Không lưu thông điệp lỗi SDK có thể chứa thông tin nhạy cảm.
                row.last_error = "queue_send_failed"
                failed += 1
            else:
                row.published_at = datetime.now(timezone.utc)
                row.last_error = None
                published += 1
    return published, failed


def fail_exhausted(db_engine, max_attempts=10, limit=100):
    """Kết thúc phiên chưa được worker nhận sau khi publisher hết lượt gửi."""
    if not 1 <= max_attempts <= 100 or not 1 <= limit <= 100:
        raise ValueError("Giới hạn gửi hàng đợi không hợp lệ")
    with Session(db_engine) as db, db.begin():
        run_ids = db.scalars(select(TrackingOutbox.run_id)
                             .join(TrackingRun, TrackingRun.id == TrackingOutbox.run_id)
                             .where(TrackingOutbox.published_at.is_(None),
                                    TrackingOutbox.publish_attempts >= max_attempts,
                                    TrackingRun.status == "queued")
                             .order_by(TrackingOutbox.created_at, TrackingOutbox.id)
                             .limit(limit).with_for_update(of=TrackingOutbox, skip_locked=True)).all()
        if not run_ids:
            return 0
        ended = db.execute(update(TrackingRun).where(
            TrackingRun.id.in_(run_ids), TrackingRun.status == "queued"
        ).values(status="failed", error_code="queue_publish_exhausted",
                 finished_at=datetime.now(timezone.utc)))
        return ended.rowcount

"""Chỉ nạp một bài giả vào database AWS dùng riêng cho kiểm thử chấp nhận."""
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.database import engine
from app.models import Brand, Post, RunPostMatch, SentimentResult, TrackingAttempt, TrackingRun
from app.sentiment import content_hash


def handler(event, context):
    host = os.environ.get("DATABASE_HOST", "")
    if (os.environ.get("TEST_ONLY_AWS_FIXTURE") != "1" or
            not host.startswith("brand-ai-check-data-") or
            not host.endswith(".rds.amazonaws.com")):
        raise RuntimeError("Chỉ sử dụng database AWS thử nghiệm riêng")
    brand_id = UUID(event["brand_id"])
    observed = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    with Session(engine()) as db, db.begin():
        if db.get(Brand, brand_id) is None:
            raise LookupError("Không tìm thấy nhãn hàng thử")
        if event.get("kind") == "alert":
            end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            for index, count in enumerate((10, 15)):
                slot = end - timedelta(days=2 - index) + timedelta(hours=8)
                snapshot = {"keywords": ["coffee"], "sources": ["tiktok"], "frequency": "daily",
                            "runTime": "08:00", "timezone": "UTC", "postLimit": 50,
                            "search_pages": 1, "comment_pages": 1, "scheduled_for": slot.isoformat()}
                run = TrackingRun(brand_id=brand_id, queued_at=slot + timedelta(minutes=1),
                                  started_at=slot + timedelta(minutes=1), finished_at=slot + timedelta(minutes=5),
                                  status="success", config_snapshot=snapshot)
                db.add(run)
                db.flush()
                db.add(TrackingAttempt(run_id=run.id, source="tiktok", keyword="coffee", status="success", result_count=count))
                for item in range(count):
                    content = f"Nội dung tiêu cực giả {index} {item}"
                    post = Post(brand_id=brand_id, source="tiktok", source_id=f"fixture-{uuid4()}",
                                url="https://example.test/alert-fixture", content=content,
                                first_seen_at=slot + timedelta(minutes=2))
                    db.add(post)
                    db.flush()
                    db.add(RunPostMatch(brand_id=brand_id, run_id=run.id, post_id=post.id,
                                        observed_at=slot + timedelta(minutes=2), content_hash=content_hash(content)))
                    db.add(SentimentResult(brand_id=brand_id, post_id=post.id, label="negative", model_id="fixture",
                                           content_hash=content_hash(content), classified_at=slot + timedelta(minutes=3)))
            return {"previous": 10, "current": 15}
        post = Post(brand_id=brand_id, source="tiktok", source_id=f"fixture-{uuid4()}",
                    url="https://example.test/ai-fixture", content="Món ăn ngon nhưng hơi cay, mong có lựa chọn ít cay hơn.",
                    first_seen_at=observed)
        run = TrackingRun(brand_id=brand_id, status="success", config_snapshot={})
        db.add_all([post, run])
        db.flush()
        db.add(RunPostMatch(brand_id=brand_id, run_id=run.id, post_id=post.id,
                            observed_at=observed, content_hash=content_hash(post.content)))
        return {"post_id": str(post.id)}

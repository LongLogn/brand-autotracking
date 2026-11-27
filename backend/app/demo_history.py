"""Tạo lịch sử giả để trình diễn cảnh báo trong môi trường demo riêng."""
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (Brand, Comment, Post, RunCommentMatch, RunPostMatch, SentimentResult,
                        TrackingAttempt, TrackingRun)
from app.sentiment import content_hash


def seed_history(db_engine, brand_id, session_id, end=None):
    end = end or datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if end.tzinfo is None or end.utcoffset() is None or end.astimezone(timezone.utc).time() != datetime.min.time():
        raise ValueError("Mốc phải là 00:00 UTC")
    end = end.astimezone(timezone.utc)
    if end > datetime.now(timezone.utc):
        raise ValueError("Chỉ dùng cửa sổ đã kết thúc")
    with Session(db_engine) as db, db.begin():
        brand = db.scalar(select(Brand).where(Brand.id == brand_id).with_for_update())
        if brand is None:
            raise LookupError("Không có nhãn hàng demo")
        existing = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id)).all()
        previous = next((run for run in existing if run.config_snapshot.get("demo_history") == str(session_id)), None)
        if previous is not None:
            return {"status": "already_seeded", "window_end": previous.config_snapshot["demo_history_end"]}
        if any(end - timedelta(days=2) <= run.queued_at < end for run in existing):
            raise ValueError("Nhãn hàng đã có phiên trong hai cửa sổ; không ghi chồng")
        for index, count in enumerate((10, 15)):
            slot = end - timedelta(days=2-index) + timedelta(hours=8)
            observed = slot + timedelta(minutes=2)
            snapshot = {"keywords": ["Mây Tea"], "sources": ["demo"], "frequency": "daily",
                        "runTime": "08:00", "timezone": "UTC", "postLimit": 1,
                        "search_pages": 1, "comment_pages": 1, "scheduled_for": slot.isoformat(),
                        "demo_history": str(session_id), "demo_history_end": end.isoformat()}
            run = TrackingRun(brand_id=brand_id, queued_at=slot + timedelta(minutes=1),
                              started_at=slot + timedelta(minutes=1), finished_at=slot + timedelta(minutes=5),
                              status="success", config_snapshot=snapshot)
            post_content = "[DỮ LIỆU GIẢ] Mây Tea: ý kiến khách hàng trong kịch bản demo."
            post = Post(brand_id=brand_id, source="demo", source_id=f"history-{session_id}-{index}",
                        url=f"https://example.invalid/demo/history/{session_id}/{index}",
                        content=post_content, posted_at=slot, first_seen_at=observed)
            db.add_all([run, post]); db.flush()
            db.add(TrackingAttempt(run_id=run.id, source="demo", keyword="Mây Tea", status="success", result_count=1))
            db.add(RunPostMatch(brand_id=brand_id, run_id=run.id, post_id=post.id,
                                observed_at=observed, content_hash=content_hash(post_content)))
            db.flush()
            for item in range(count):
                content = f"[DỮ LIỆU GIẢ] {('Đồ uống quá ngọt', 'Giao hàng chậm')[item % 2]} — mẫu {index+1}.{item+1}."
                comment = Comment(brand_id=brand_id, post_id=post.id, source_id=f"history-{session_id}-{index}-{item}",
                                  content=content, posted_at=slot)
                db.add(comment); db.flush()
                db.add(RunCommentMatch(brand_id=brand_id, run_id=run.id, post_id=post.id, comment_id=comment.id,
                                       observed_at=observed, content_hash=content_hash(content)))
                db.add(SentimentResult(brand_id=brand_id, comment_id=comment.id, content_hash=content_hash(content),
                                       label="negative", model_id="demo-fixture-labels", classified_at=observed))
        return {"status": "seeded", "window_end": end.isoformat(), "previous": 10, "current": 15}


def handler(event, context):
    host = os.environ.get("DATABASE_HOST", "")
    if (os.environ.get("DEMO_HISTORY_ENABLED") != "true" or not host.startswith("brand-demo-")
            or not host.endswith(".rds.amazonaws.com") or os.environ.get("DATABASE_NAME") != "brand_tracking"):
        raise RuntimeError("Chỉ nạp vào database AWS demo riêng")
    brand_id, session_id = UUID(os.environ["DEMO_BRAND_ID"]), UUID(os.environ["DEMO_SESSION_ID"])
    if event.get("brand_id") != str(brand_id) or event.get("session_id") != str(session_id):
        raise ValueError("Nhãn hàng hoặc phiên demo không khớp")
    return seed_history(engine(), brand_id, session_id)


def main():
    import argparse
    import json
    from sqlalchemy import create_engine
    from app.demo_stream import demo_url

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand-id", type=UUID, required=True)
    parser.add_argument("--session-id", type=UUID, required=True)
    args = parser.parse_args()
    try:
        url = demo_url(os.environ.get("DEMO_DATABASE_URL"))
    except ValueError as exc:
        parser.error(str(exc))
    db_engine = create_engine(url)
    try:
        print(json.dumps(seed_history(db_engine, args.brand_id, args.session_id)))
    finally:
        db_engine.dispose()


if __name__ == "__main__":
    main()

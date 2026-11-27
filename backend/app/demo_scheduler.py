"""Lập lịch hữu hạn cho một nhãn hàng demo duy nhất trên môi trường riêng."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, BrandKeyword, BrandSource, TrackingConfig, TrackingOutbox, TrackingRun


def enqueue_demo(engine, brand_id, session_id, max_batches, expires_at, current=None, interval_minutes=1,
                 auto_batches=None, manual=False):
    """Xếp đợt demo tiếp theo.

    Lịch tự động chỉ xếp tới `auto_batches` đợt (mặc định bằng `max_batches`) và cách
    nhau ít nhất `interval_minutes`. Đợt sau đó chỉ được xếp khi người vận hành yêu
    cầu (`manual=True`), không chờ khoảng cách, nhưng vẫn không vượt `max_batches`.
    """
    current = current or datetime.now(timezone.utc)
    if not isinstance(brand_id, UUID) or not isinstance(session_id, UUID):
        raise ValueError("Demo cần UUID nhãn hàng và phiên")
    auto_batches = max_batches if auto_batches is None else auto_batches
    if (current.tzinfo is None or expires_at.tzinfo is None or not 1 <= max_batches <= 20
            or type(interval_minutes) is not int or not 1 <= interval_minutes <= 3
            or type(auto_batches) is not int or not 1 <= auto_batches <= max_batches):
        raise ValueError("Giới hạn demo không hợp lệ")
    if current >= expires_at:
        return None
    with Session(engine) as db, db.begin():
        brand = db.scalar(select(Brand).where(Brand.id == brand_id).with_for_update())
        config = db.get(TrackingConfig, brand_id)
        if brand is None or config is None or not config.active:
            return None
        runs = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id)).all()
        session_runs = [run for run in runs if run.config_snapshot.get("demo_session") == str(session_id)]
        batch_count = len(session_runs)
        if batch_count >= max_batches:
            return None
        if manual:
            if batch_count < auto_batches:
                return None
        elif batch_count >= auto_batches:
            return None
        elif session_runs and current < max(run.queued_at for run in session_runs) + timedelta(minutes=interval_minutes):
            return None
        if any(run.status in {"queued", "running"} for run in runs):
            return None
        keywords = list(db.scalars(select(BrandKeyword.keyword).where(BrandKeyword.brand_id == brand_id).order_by(BrandKeyword.keyword)))
        sources = list(db.scalars(select(BrandSource.source).where(BrandSource.brand_id == brand_id)))
        if not keywords or sources != ["tiktok"] or not 1 <= config.post_limit <= 50:
            raise ValueError("Cấu hình nhãn hàng demo không hợp lệ")
        snapshot = {"keywords": keywords, "sources": sources, "postLimit": config.post_limit,
                    "frequency": config.frequency, "runTime": config.run_time, "timezone": config.timezone,
                    "search_pages": 1, "comment_pages": 1, "demo_session": str(session_id), "demo_batch": batch_count + 1}
        run = TrackingRun(brand_id=brand_id, status="queued", queued_at=current, config_snapshot=snapshot)
        db.add(run)
        db.flush()
        db.add(TrackingOutbox(run_id=run.id, created_at=current))
        return run.id

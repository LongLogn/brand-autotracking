"""Điều phối lịch thử nghiệm qua PostgreSQL; mỗi lần quét tạo tối đa một phiên mỗi lịch."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, BrandKeyword, BrandSource, TrackingConfig, TrackingOutbox, TrackingRun


def next_slot(after, frequency, run_time, timezone_name, weekday=None):
    """Lấy lần sau mốc UTC; giờ không tồn tại do DST bị bỏ qua, giờ lặp dùng lần đầu."""
    if after.tzinfo is None:
        raise ValueError("Mốc thời gian phải có múi giờ")
    zone = ZoneInfo(timezone_name)
    local = after.astimezone(zone)
    hour, minute = map(int, run_time.split(":"))
    times = [time(hour, minute)]
    if frequency == "twice-daily":
        times.append(time((hour + 12) % 24, minute))
    elif frequency not in ("daily", "weekly"):
        raise ValueError("Tần suất không hợp lệ")
    weekday = local.weekday() if weekday is None else weekday
    for offset in range(15):
        day = local.date() + timedelta(days=offset)
        if frequency == "weekly" and day.weekday() != weekday:
            continue
        for at in sorted(times):
            candidate = datetime.combine(day, at, tzinfo=zone).replace(fold=0)
            utc = candidate.astimezone(timezone.utc)
            # Vòng về cùng giờ địa phương mới là một thời điểm tồn tại.
            if utc.astimezone(zone).replace(tzinfo=None) != candidate.replace(tzinfo=None):
                continue
            if utc > after:
                return utc
    raise ValueError("Không tìm được lịch tiếp theo")


def enqueue_due(db_engine, current=None, limit=20):
    """Khóa nhãn hàng, xếp hoặc ghi bỏ qua và tiến lịch trong cùng giao dịch."""
    current = current or datetime.now(timezone.utc)
    if current.tzinfo is None or not 1 <= limit <= 100:
        raise ValueError("Mốc hoặc giới hạn không hợp lệ")
    with Session(db_engine) as db:
        ids = db.scalars(select(TrackingConfig.brand_id).where(
            TrackingConfig.active.is_(True),
            (TrackingConfig.next_run_at.is_(None)) | (TrackingConfig.next_run_at <= current),
        ).order_by(TrackingConfig.next_run_at.asc().nullsfirst(), TrackingConfig.brand_id).limit(limit)).all()
    created = 0
    for brand_id in ids:
        with Session(db_engine) as db, db.begin():
            brand = db.scalar(select(Brand).where(Brand.id == brand_id).with_for_update(skip_locked=True))
            if brand is None:
                continue
            cfg = db.get(TrackingConfig, brand_id)
            if cfg is None or not cfg.active:
                continue
            due = cfg.next_run_at
            if due is None:
                cfg.next_run_at = next_slot(current, cfg.frequency, cfg.run_time, cfg.timezone)
                continue
            if due > current:
                continue
            weekday = due.astimezone(ZoneInfo(cfg.timezone)).weekday()
            cfg.next_run_at = next_slot(current, cfg.frequency, cfg.run_time, cfg.timezone, weekday)
            keywords = list(db.scalars(select(BrandKeyword.keyword).where(BrandKeyword.brand_id == brand_id).order_by(BrandKeyword.keyword)))
            sources = list(db.scalars(select(BrandSource.source).where(BrandSource.brand_id == brand_id).order_by(BrandSource.source)))
            snapshot = {"keywords": keywords, "sources": sources, "postLimit": cfg.post_limit,
                        "lookbackDays": cfg.lookback_days,
                        "frequency": cfg.frequency, "runTime": cfg.run_time, "timezone": cfg.timezone,
                        "search_pages": 1, "comment_pages": 1, "scheduled_for": due.astimezone(timezone.utc).isoformat()}
            active = db.scalar(select(TrackingRun.id).where(TrackingRun.brand_id == brand_id,
                               TrackingRun.status.in_(["queued", "running"])))
            if not keywords or not sources or not 1 <= cfg.post_limit <= 50:
                status, error = "skipped", "invalid_config"
            elif active:
                status, error = "skipped", "previous_run_active"
            else:
                status, error = "queued", None
            run = TrackingRun(brand_id=brand_id, queued_at=current, status=status, error_code=error,
                              finished_at=current if status == "skipped" else None, config_snapshot=snapshot)
            db.add(run)
            db.flush()
            if status == "queued":
                db.add(TrackingOutbox(run_id=run.id, created_at=current))
            created += 1
    return created

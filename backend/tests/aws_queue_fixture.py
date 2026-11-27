"""Fixture lịch/hàng đợi chỉ chạy trên database AWS thử nghiệm riêng."""
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (Brand, BrandKeyword, BrandSource, FirecrawlCreditReservation, Post, TrackingAttempt, TrackingConfig,
                        TrackingOutbox, TrackingRun, User)


def handler(event, context):
    host = os.environ.get("DATABASE_HOST", "")
    if (os.environ.get("TEST_ONLY_AWS_FIXTURE") != "1" or
            not host.startswith("brand-queue-check-data-") or not host.endswith(".rds.amazonaws.com")):
        raise RuntimeError("Chỉ sử dụng database AWS thử nghiệm riêng")
    action = event.get("action")
    now = datetime.now(timezone.utc)
    with Session(engine()) as db, db.begin():
        if action == "find":
            ids = db.scalars(select(Brand.id).join(User, Brand.owner_id == User.id)
                             .where(User.cognito_sub.like("queue-fixture-%"))).all()
            return {"brand_ids": [str(value) for value in ids]}
        if action == "create":
            user = User(cognito_sub=f"queue-fixture-{uuid4()}")
            db.add(user)
            db.flush()
            brand = Brand(owner_id=user.id, name="Queue fixture")
            db.add(brand)
            db.flush()
            db.add_all([TrackingConfig(brand_id=brand.id, frequency="daily", run_time="08:00",
                                       timezone="UTC", post_limit=1, active=True,
                                       next_run_at=now - timedelta(minutes=1)),
                        BrandKeyword(brand_id=brand.id, keyword="coffee"),
                        BrandSource(brand_id=brand.id, source="tiktok")])
            return {"brand_id": str(brand.id)}
        brand_id = UUID(event["brand_id"])
        cfg = db.get(TrackingConfig, brand_id)
        if cfg is None:
            raise LookupError("Không tìm thấy cấu hình thử")
        if action == "expire":
            run = TrackingRun(brand_id=brand_id, status="running", queued_at=now - timedelta(minutes=3),
                              started_at=now - timedelta(minutes=3), lease_token=uuid4(),
                              lease_expires_at=now - timedelta(minutes=1),
                              config_snapshot={"keywords": ["coffee"], "sources": ["tiktok"], "postLimit": 1})
            db.add(run)
            db.flush()
            return {"expired_run_id": str(run.id)}
        if action == "pause":
            cfg.active = False
            cfg.next_run_at = now - timedelta(minutes=1)
            return {"paused": True}
        if action == "inspect":
            rows = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id).order_by(TrackingRun.queued_at)).all()
            runs = []
            for row in rows:
                outbox = db.scalar(select(TrackingOutbox).where(TrackingOutbox.run_id == row.id))
                attempts = db.scalar(select(func.count()).select_from(TrackingAttempt).where(TrackingAttempt.run_id == row.id))
                runs.append({"id": str(row.id), "status": row.status, "error": row.error_code,
                             "event_id": str(outbox.id) if outbox else None,
                             "published": bool(outbox and outbox.published_at), "attempts": attempts,
                             "scheduled": bool(row.config_snapshot.get("scheduled_for")),
                             "recovered_from": row.config_snapshot.get("recovered_from")})
            post_count = db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id))
            reservation = db.get(FirecrawlCreditReservation, now.date())
            return {"runs": runs, "post_count": post_count, "credits_reserved": reservation.reserved if reservation else 0}
        raise ValueError("Tác vụ fixture không hợp lệ")

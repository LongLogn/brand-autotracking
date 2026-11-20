"""Kiểm thử lịch và khóa đồng thời trên database thử nghiệm."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Brand, BrandKeyword, BrandSource, TrackingConfig, TrackingOutbox, TrackingRun, User
from app.scheduler import enqueue_due, next_slot

UTC = timezone.utc


class SlotTests(unittest.TestCase):
    def test_daily_twice_and_weekly_local_time(self):
        now = datetime(2026, 11, 16, 2, tzinfo=UTC)  # 09:00 tại Việt Nam
        self.assertEqual(next_slot(now, "daily", "08:00", "Asia/Ho_Chi_Minh"), datetime(2026, 11, 17, 1, tzinfo=UTC))
        self.assertEqual(next_slot(now, "twice-daily", "08:00", "Asia/Ho_Chi_Minh"), datetime(2026, 11, 16, 13, tzinfo=UTC))
        self.assertEqual(next_slot(now, "weekly", "08:00", "Asia/Ho_Chi_Minh"), datetime(2026, 11, 23, 1, tzinfo=UTC))

    def test_nonexistent_dst_time_skips_day(self):
        now = datetime(2026, 3, 8, 6, tzinfo=UTC)
        self.assertEqual(next_slot(now, "daily", "02:30", "America/New_York"), datetime(2026, 3, 9, 6, 30, tzinfo=UTC))

    def test_dst_repeated_hour_is_not_run_twice(self):
        first = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
        self.assertEqual(next_slot(first, "daily", "01:30", "America/New_York"), datetime(2026, 11, 2, 6, 30, tzinfo=UTC))


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class SchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"])

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def make_brand(self, *, active=True):
        now = datetime.now(UTC)
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="scheduler test"); db.add(brand); db.flush()
            db.add(TrackingConfig(brand_id=brand.id, frequency="daily", run_time="08:00", timezone="Asia/Ho_Chi_Minh",
                                  post_limit=1, active=active, next_run_at=now - timedelta(minutes=1)))
            db.add(BrandKeyword(brand_id=brand.id, keyword="example"))
            db.add(BrandSource(brand_id=brand.id, source="tiktok"))
            return brand.id, now

    def test_due_once_and_snapshot(self):
        brand, now = self.make_brand()
        self.assertEqual(enqueue_due(self.engine, now), 1)
        self.assertEqual(enqueue_due(self.engine, now), 0)
        with Session(self.engine) as db:
            run = db.scalar(select(TrackingRun).where(TrackingRun.brand_id == brand))
            self.assertEqual(run.status, "queued")
            self.assertIsNotNone(db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == run.id)))
            self.assertEqual(run.config_snapshot["keywords"], ["example"])
            self.assertGreater(db.get(TrackingConfig, brand).next_run_at, now)
            run.status = "success"; db.commit()

    def test_paused_and_active_run_skipped(self):
        paused, now = self.make_brand(active=False)
        brand, now = self.make_brand()
        with Session(self.engine) as db, db.begin():
            db.add(TrackingRun(brand_id=brand, status="running", queued_at=now, started_at=now, config_snapshot={}))
        self.assertEqual(enqueue_due(self.engine, now), 1)
        with Session(self.engine) as db:
            rows = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand)).all()
            self.assertEqual(sorted(r.status for r in rows), ["running", "skipped"])
            self.assertEqual(next(r for r in rows if r.status == "skipped").error_code, "previous_run_active")
            skipped = next(r for r in rows if r.status == "skipped")
            self.assertIsNone(db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == skipped.id)))
            self.assertEqual(db.scalars(select(TrackingRun).where(TrackingRun.brand_id == paused)).all(), [])
            next(r for r in rows if r.status == "running").status = "success"; db.commit()

    def test_concurrent_scheduler_does_not_create_two_runs(self):
        brand, now = self.make_brand()
        barrier = Barrier(2)
        def scan():
            barrier.wait(timeout=10)
            return enqueue_due(self.engine, now)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: scan(), range(2)))
        self.assertEqual(sum(results), 1)
        with Session(self.engine) as db:
            runs = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand)).all()
            self.assertEqual(len(runs), 1)
            runs[0].status = "success"; db.commit()


if __name__ == "__main__":
    unittest.main()

"""Kiểm thử hàng đợi phân loại với PostgreSQL và provider giả."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import Brand, BrandKeyword, BrandSource, SentimentResult, SentimentWork, TrackingConfig, User
from app.sentiment import (SentimentBudgetExhausted, SentimentLeaseLost, SentimentProviderError, SentimentRateLimited, check_sentiment_lease,
                           claim_sentiment_work, classify_content, classify_run, finish_sentiment_work)
from app.tracking import run_once
from tests.test_tracking_flow import FakeProvider


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class SentimentWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"])

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def make_run(self):
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="sentiment queue"); db.add(brand); db.flush()
            db.add(TrackingConfig(brand_id=brand.id, frequency="daily", run_time="08:00", timezone="UTC", post_limit=1, active=True))
            db.add(BrandKeyword(brand_id=brand.id, keyword="sample")); db.add(BrandSource(brand_id=brand.id, source="tiktok"))
            brand_id = brand.id
        run_id, status = run_once(self.engine, brand_id, FakeProvider())
        self.assertEqual(status, "success")
        return brand_id, run_id

    def make_due(self, run_id):
        with Session(self.engine) as db, db.begin():
            db.get(SentimentWork, run_id).next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    def test_batches_resume_without_reclassifying_completed_items(self):
        brand, run_id = self.make_run()
        calls = []
        def provider(content):
            calls.append(content)
            return "negative"
        with patch("app.sentiment.reserve_daily_call"):
            first = claim_sentiment_work(self.engine, run_id=run_id)
            result = classify_run(self.engine, run_id, provider, "model", max_calls=1, daily_limit=10,
                                  before_write=lambda db: check_sentiment_lease(db, *first))
            self.assertEqual((result["processed"], result["remaining"]), (1, 1))
            self.assertEqual(finish_sentiment_work(self.engine, *first, result), "pending")
            self.assertIsNone(claim_sentiment_work(self.engine, run_id=run_id))
            self.make_due(run_id)
            second = claim_sentiment_work(self.engine, run_id=run_id)
            result = classify_run(self.engine, run_id, provider, "model", max_calls=1, daily_limit=10,
                                  before_write=lambda db: check_sentiment_lease(db, *second))
            self.assertEqual(finish_sentiment_work(self.engine, *second, result), "complete")
        self.assertEqual(len(calls), 2)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(SentimentResult).where(SentimentResult.brand_id == brand)), 2)
        self.assertIsNone(claim_sentiment_work(self.engine, run_id=run_id))

    def test_failed_calls_are_retried_at_most_three_times(self):
        _, run_id = self.make_run()
        def fail(_):
            raise SentimentProviderError("provider")
        with patch("app.sentiment.reserve_daily_call"):
            for attempt in range(3):
                if attempt: self.make_due(run_id)
                claim = claim_sentiment_work(self.engine, run_id=run_id)
                result = classify_run(self.engine, run_id, fail, "model", max_calls=2, daily_limit=10,
                                      before_write=lambda db: check_sentiment_lease(db, *claim))
                self.assertEqual(result["remaining"], 2)
                self.assertEqual(finish_sentiment_work(self.engine, *claim, result), "failed" if attempt == 2 else "pending")
        with Session(self.engine) as db:
            self.assertEqual(db.get(SentimentWork, run_id).failures, 3)
        self.assertIsNone(claim_sentiment_work(self.engine, run_id=run_id))

    def test_budget_exhaustion_waits_until_next_utc_day_without_failure(self):
        _, run_id = self.make_run()
        with patch("app.sentiment.reserve_daily_call", side_effect=SentimentBudgetExhausted()):
            claim = claim_sentiment_work(self.engine, run_id=run_id)
            result = classify_run(self.engine, run_id, lambda _: "negative", "model", max_calls=2, daily_limit=10,
                                  before_write=lambda db: check_sentiment_lease(db, *claim))
            self.assertTrue(result["daily_limit_reached"])
            self.assertEqual(finish_sentiment_work(self.engine, *claim, result), "pending")
        with Session(self.engine) as db:
            row = db.get(SentimentWork, run_id)
            self.assertEqual(row.failures, 0)
            self.assertGreater(row.next_attempt_at, datetime.now(timezone.utc))

    def test_rate_exhaustion_waits_for_next_minute_without_failure(self):
        _, run_id = self.make_run()
        with patch("app.sentiment.reserve_daily_call", side_effect=SentimentRateLimited()):
            claim = claim_sentiment_work(self.engine, run_id=run_id)
            result = classify_run(self.engine, run_id, lambda _: "negative", "model", max_calls=2, daily_limit=10,
                                  before_write=lambda db: check_sentiment_lease(db, *claim))
            self.assertTrue(result["rate_limit_reached"])
            self.assertEqual(finish_sentiment_work(self.engine, *claim, result), "pending")
        with Session(self.engine) as db:
            row = db.get(SentimentWork, run_id)
            self.assertEqual(row.failures, 0)
            self.assertGreater(row.next_attempt_at, datetime.now(timezone.utc))

    def test_expired_lease_fences_late_results_and_concurrent_claims(self):
        brand, run_id = self.make_run()
        barrier = Barrier(2)
        def claim(_):
            barrier.wait(timeout=5)
            return claim_sentiment_work(self.engine, run_id=run_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(claim, range(2)))
        self.assertEqual(sum(item is not None for item in claims), 1)
        old = next(item for item in claims if item is not None)
        with Session(self.engine) as db, db.begin():
            db.get(SentimentWork, run_id).lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        new = claim_sentiment_work(self.engine, run_id=run_id)
        self.assertNotEqual(old[1], new[1])
        from app.models import Post
        with Session(self.engine) as db:
            post_id = db.scalar(select(Post.id).where(Post.brand_id == brand))
        with self.assertRaises(SentimentLeaseLost):
            classify_content(self.engine, brand, "post", post_id, lambda _: "negative", "model",
                             before_write=lambda db: check_sentiment_lease(db, *old))
        with self.assertRaises(SentimentLeaseLost):
            finish_sentiment_work(self.engine, *old, None)
        with Session(self.engine) as db:
            self.assertIsNone(db.scalar(select(SentimentResult).where(SentimentResult.post_id == post_id)))

"""Kiểm thử đánh giá và lưu lịch sử cảnh báo trên PostgreSQL thử."""
import os
import io
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import current_subject
from app.database import session
from app.main import app
from app.models import Alert, AlertRule, Brand, User
from tests import test_alert_evaluation as fixtures


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class AlertApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_size=2, max_overflow=0, pool_timeout=2)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.client = TestClient(app)
        def db_session():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[session] = db_session

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def create_rule(self, before=10, after=15, absolute=None):
        brand, runs = fixtures.ComparisonTests.fixture(self, before, after)
        with Session(self.engine) as db, db.begin():
            subject = db.scalar(select(User.cognito_sub).join(Brand, Brand.owner_id == User.id).where(Brand.id == brand))
            db.add(AlertRule(brand_id=brand, content_type="post", enabled=True, growth_percent=50,
                             window_days=1, minimum_current=5, absolute_threshold=absolute))
        app.dependency_overrides[current_subject] = lambda: subject
        return brand, runs

    def evaluate(self, brand):
        return self.client.post(f"/brands/{brand}/alert-rules/post/evaluate", json={"window_end": fixtures.END.isoformat()})

    def test_threshold_and_deduplication_with_concurrent_requests(self):
        brand, _ = self.create_rule()
        barrier = Barrier(2)
        def evaluate(_):
            barrier.wait(timeout=5)
            return self.evaluate(brand)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(evaluate, range(2)))
        self.assertEqual([r.status_code for r in responses], [200, 200])
        self.assertEqual([r.json()["status"] for r in responses], ["triggered", "triggered"])
        self.assertEqual(responses[0].json()["alert"]["id"], responses[1].json()["alert"]["id"])
        self.assertEqual((responses[0].json()["previous_negative"], responses[0].json()["current_negative"]), (10, 15))
        self.assertEqual(len(self.client.get(f"/brands/{brand}/alerts").json()), 1)
        app.dependency_overrides[current_subject] = lambda: str(uuid4())
        self.assertEqual(self.client.get(f"/brands/{brand}/alerts").status_code, 404)
        self.assertEqual(self.evaluate(brand).status_code, 404)

    def test_below_threshold_and_zero_baseline(self):
        brand, _ = self.create_rule(after=14)
        self.assertEqual(self.evaluate(brand).json()["status"], "not_triggered")
        self.assertEqual(self.client.get(f"/brands/{brand}/alerts").json(), [])
        brand, _ = self.create_rule(before=0, after=15)
        response = self.evaluate(brand).json()
        self.assertEqual((response["status"], response["reason"]), ("insufficient_data", "zero_baseline"))
        with Session(self.engine) as db, db.begin():
            db.get(AlertRule, (brand, "post")).absolute_threshold = 15
        self.assertEqual(self.evaluate(brand).json()["status"], "triggered")

    def test_missing_coverage_disabled_and_invalid_windows(self):
        brand, runs = self.create_rule(before=1, after=1)
        from app.models import TrackingRun
        with Session(self.engine) as db, db.begin():
            db.get(TrackingRun, runs[1]).status = "failed"
        self.assertEqual(self.evaluate(brand).json()["status"], "insufficient_data")
        with Session(self.engine) as db, db.begin():
            db.get(AlertRule, (brand, "post")).enabled = False
        self.assertEqual(self.evaluate(brand).json()["status"], "disabled")
        path = f"/brands/{brand}/alert-rules/post/evaluate"
        for bad in ("2026-01-03T01:00:00Z", "2026-01-03T00:00:00", "9999-01-01T00:00:00Z"):
            self.assertEqual(self.client.post(path, json={"window_end": bad}).status_code, 422)
        with Session(self.engine) as db:
            self.assertEqual(db.scalars(select(Alert).where(Alert.brand_id == brand)).all(), [])

    def test_worker_evaluates_enabled_rules_after_tracking(self):
        from app import lambda_worker
        brand, runs = self.create_rule()
        with patch.dict(os.environ, {"ALERT_EVALUATION_ENABLED": "true"}), \
             patch.object(lambda_worker, "datetime") as clock, \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            clock.now.return_value = fixtures.END
            lambda_worker.run_alerts_if_enabled(self.engine, runs[-1])
            event = json.loads(output.getvalue())
            self.assertEqual((event["event"], event["status"]), ("alert_evaluation", "triggered"))
        self.assertEqual(len(self.client.get(f"/brands/{brand}/alerts").json()), 1)

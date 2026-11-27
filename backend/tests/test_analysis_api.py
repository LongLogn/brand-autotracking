"""Kiểm thử API phân tích với PostgreSQL và model giả, không gọi AWS."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import current_subject
from app.database import session
from app.main import app
from app.models import AnalysisJob, Brand, Post, RunPostMatch, TrackingRun, User
from app.sentiment import content_hash

UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)
END = START + timedelta(days=1)


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class AnalysisApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_size=2, max_overflow=0, pool_timeout=3)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.client = TestClient(app)
        self.subject = str(uuid4())
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=self.subject); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="AI fixture"); db.add(brand); db.flush()
            self.brand = brand.id
        def db_session():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[session] = db_session
        app.dependency_overrides[current_subject] = lambda: self.subject
        self.env = patch.dict(os.environ, {"ANALYSIS_ENABLED": "true", "ANALYSIS_MODEL_ID": "fake-model", "BEDROCK_DAILY_CALL_LIMIT": "3"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        app.dependency_overrides.clear()
        self.client.close()

    def add_post(self):
        with Session(self.engine) as db, db.begin():
            post = Post(brand_id=self.brand, source="tiktok", source_id=str(uuid4()), url="https://example.test/post",
                        content="Món ăn rất cay", first_seen_at=START + timedelta(hours=1))
            run = TrackingRun(brand_id=self.brand, status="success", config_snapshot={})
            db.add_all([post, run]); db.flush()
            db.add(RunPostMatch(brand_id=self.brand, run_id=run.id, post_id=post.id,
                                observed_at=START + timedelta(hours=1), content_hash=content_hash(post.content)))
            return post.id

    def call(self, key, body=None):
        return self.client.post(f"/brands/{self.brand}/analyses", headers={"Idempotency-Key": str(key)},
                                json=body or {"window_start": START.isoformat(), "window_end": END.isoformat()})

    @staticmethod
    def provider(data):
        return [{"summary": "Khách đề cập vị cay", "recommendation": "Cân nhắc thêm lựa chọn", "evidence_ids": [data.items[0].id]}]

    def test_success_is_idempotent_and_owner_scoped(self):
        post = self.add_post(); key = uuid4(); provider = Mock(side_effect=self.provider)
        with patch("app.main.analysis_provider", return_value=provider), patch("app.analysis.reserve_daily_call") as reserve:
            first, again = self.call(key), self.call(key)
            self.assertEqual((first.status_code, again.status_code), (200, 200))
            self.assertEqual(first.json()["id"], again.json()["id"])
            self.assertEqual(first.json()["status"], "success")
            self.assertEqual(first.json()["findings"][0]["evidence_ids"], [f"post:{post}"])
            self.assertNotIn("Món ăn rất cay", str(first.json()["evidence"]))
            self.assertEqual(provider.call_count, 1)
            reserve.assert_called_once_with(self.engine, 3)
            changed = {"window_start": START.isoformat(), "window_end": (END + timedelta(hours=1)).isoformat()}
            self.assertEqual(self.call(key, changed).status_code, 409)
        self.assertEqual(len(self.client.get(f"/brands/{self.brand}/analyses").json()), 1)
        self.subject = str(uuid4())
        self.assertEqual(self.client.get(f"/brands/{self.brand}/analyses").status_code, 404)
        self.assertEqual(self.call(uuid4()).status_code, 404)

    def test_empty_data_does_not_call_model_or_reserve(self):
        provider = Mock()
        with patch("app.main.analysis_provider", return_value=provider), patch("app.analysis.reserve_daily_call") as reserve:
            response = self.call(uuid4())
        self.assertEqual((response.json()["status"], response.json()["error_code"]), ("failed", "empty_data"))
        provider.assert_not_called(); reserve.assert_not_called()

    def test_concurrent_request_reuses_running_job(self):
        self.add_post(); key = uuid4(); entered = Event(); release = Event()
        def slow(data):
            entered.set(); self.assertTrue(release.wait(timeout=5)); return self.provider(data)
        provider = Mock(side_effect=slow)
        with patch("app.main.analysis_provider", return_value=provider), patch("app.analysis.reserve_daily_call") as reserve:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.call, key)
                self.assertTrue(entered.wait(timeout=5))
                second = pool.submit(self.call, key).result(timeout=5)
                release.set()
                finished = first.result(timeout=5)
        self.assertEqual(second.json()["status"], "running")
        self.assertEqual(finished.json()["status"], "success")
        self.assertEqual(second.json()["id"], finished.json()["id"])
        self.assertEqual(provider.call_count, 1); reserve.assert_called_once()

    def test_stale_job_is_failed_and_late_response_cannot_overwrite(self):
        from app.analysis import reconcile_stale_analyses
        self.add_post(); key = uuid4(); entered = Event(); release = Event()
        def slow(data):
            entered.set(); self.assertTrue(release.wait(timeout=5)); return self.provider(data)
        provider = Mock(side_effect=slow)
        with patch("app.main.analysis_provider", return_value=provider), patch("app.analysis.reserve_daily_call") as reserve:
            with ThreadPoolExecutor(max_workers=1) as pool:
                task = pool.submit(self.call, key)
                self.assertTrue(entered.wait(timeout=5))
                with Session(self.engine) as db, db.begin():
                    job = db.scalar(select(AnalysisJob).where(AnalysisJob.brand_id == self.brand, AnalysisJob.request_key == key))
                    job.created_at = datetime.now(UTC) - timedelta(minutes=3)
                self.assertEqual(reconcile_stale_analyses(self.engine, brand_id=self.brand), 1)
                release.set()
                finished = task.result(timeout=5)
            again = self.call(key)
        for response in (finished, again):
            self.assertEqual((response.json()["status"], response.json()["error_code"]), ("failed", "timeout"))
            self.assertIsNone(response.json()["findings"])
        self.assertEqual(provider.call_count, 1); reserve.assert_called_once()

    def test_history_reconciles_stale_jobs_only_for_owner(self):
        key = uuid4()
        with Session(self.engine) as db, db.begin():
            db.add(AnalysisJob(brand_id=self.brand, request_key=key, status="running", window_start=START,
                               window_end=END, model_id="fake", created_at=datetime.now(UTC) - timedelta(minutes=3)))
        self.subject = str(uuid4())
        self.assertEqual(self.client.get(f"/brands/{self.brand}/analyses").status_code, 404)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(AnalysisJob.status).where(AnalysisJob.brand_id == self.brand)), "running")
        with Session(self.engine) as db:
            self.subject = db.get(User, db.get(Brand, self.brand).owner_id).cognito_sub
        history = self.client.get(f"/brands/{self.brand}/analyses")
        self.assertEqual((history.json()[0]["status"], history.json()[0]["error_code"]), ("failed", "timeout"))

    def test_budget_provider_errors_and_disabled_mode_do_not_return_fake_results(self):
        from app.analysis import AnalysisProviderError
        from app.sentiment import SentimentBudgetExhausted
        self.add_post()
        provider = Mock(side_effect=AnalysisProviderError("unsafe provider detail"))
        with patch("app.main.analysis_provider", return_value=provider), \
             patch("app.analysis.reserve_daily_call", side_effect=SentimentBudgetExhausted("budget")):
            budget = self.call(uuid4())
        self.assertEqual((budget.json()["status"], budget.json()["error_code"]), ("failed", "budget_exhausted"))
        provider.assert_not_called()
        with patch("app.main.analysis_provider", return_value=provider), patch("app.analysis.reserve_daily_call"):
            failed = self.call(uuid4())
        self.assertEqual((failed.json()["status"], failed.json()["error_code"]), ("failed", "provider_error"))
        self.assertIsNone(failed.json()["findings"])
        self.assertNotIn("unsafe provider detail", failed.text)
        with patch.dict(os.environ, {"ANALYSIS_ENABLED": "false"}):
            self.assertEqual(self.call(uuid4()).status_code, 503)

    def test_bad_range_and_missing_key_are_rejected(self):
        with patch("app.main.analysis_provider", return_value=Mock()), patch("app.analysis.reserve_daily_call") as reserve:
            bad = {"window_start": START.isoformat(), "window_end": START.isoformat()}
            self.assertEqual(self.call(uuid4(), bad).status_code, 422)
            self.assertEqual(self.client.post(f"/brands/{self.brand}/analyses", json=bad).status_code, 422)
            reserve.assert_not_called()

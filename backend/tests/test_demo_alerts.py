"""Kịch bản demo theo phút: nhãn giả lập, cảnh báo tỷ lệ, email và API."""
import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from botocore.exceptions import ClientError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.demo_alerts import alert_message, notify_alert, ratio_increase, sentiment_timeline
from app.demo_stream import DEMO_SCENARIO, DemoProvider, demo_label
from app.models import (Alert, AlertRule, Brand, BrandKeyword, BrandSource, Comment, SentimentResult, SentimentWork,
                        TrackingConfig, TrackingOutbox, TrackingRun, User)


class ScenarioTests(unittest.TestCase):
    def test_scenario_batches_have_expected_composition(self):
        for batch, plan in DEMO_SCENARIO.items():
            comments = DemoProvider(f"b{batch}", None, batch).comments("x")
            labels = [demo_label(item["text"]) for item in comments]
            self.assertEqual(len(comments), sum(plan.values()))
            self.assertEqual(len({item["cid"] for item in comments}), len(comments))
            for label, count in plan.items():
                self.assertEqual(labels.count(label), count)
            self.assertTrue(all(item["text"].startswith("[DỮ LIỆU GIẢ] ") for item in comments))
        # Không tách nhóm theo nhãn: 10 bình luận đầu đã có nhiều nhãn.
        first = [demo_label(item["text"]) for item in DemoProvider("b", None, 1).comments("x")[:10]]
        self.assertGreater(len(set(first)), 1)

    def test_unknown_text_has_no_label(self):
        self.assertIsNone(demo_label("Gà rán bị khô, kém giòn."))
        self.assertIsNone(demo_label("[DỮ LIỆU GIẢ] câu khác"))
        self.assertEqual(demo_label("[DỮ LIỆU GIẢ] Giao hàng chậm quá. (mẫu 2.4)"), "negative")

    def test_ratio_rule_matches_plan(self):
        self.assertEqual(ratio_increase(20, 100, 60, 200, 50, 10), ("triggered", "ratio_growth"))
        self.assertEqual(ratio_increase(20, 100, 30, 150, 50, 10), ("not_triggered", "ratio_growth"))
        self.assertEqual(ratio_increase(60, 200, 65, 300, 50, 10), ("not_triggered", "ratio_growth"))
        self.assertEqual(ratio_increase(60, 200, 60, 200, 50, 10), ("not_triggered", "ratio_growth"))
        self.assertEqual(ratio_increase(2, 10, 9, 20, 50, 10), ("not_triggered", "ratio_growth"))
        self.assertEqual(ratio_increase(0, 10, 5, 20, 50, 1), ("insufficient_data", "zero_baseline"))
        self.assertEqual(ratio_increase(0, 10, 5, 20, 50, 1, 3), ("triggered", "absolute_threshold"))

    def test_message_has_link_and_ascii_subject(self):
        alert = Alert(id=uuid4(), brand_id=uuid4(), previous_negative=20, previous_total=100,
                      current_negative=60, current_total=200, growth_percent=50)
        subject, body = alert_message(alert, "KFCC\n", "https://example.cloudfront.net/")
        self.assertTrue(all(32 <= ord(ch) < 127 for ch in subject))
        self.assertIn("KFCC", subject)
        self.assertIn(f"https://example.cloudfront.net/?brand={alert.brand_id}&alert={alert.id}", body)
        self.assertIn("20%", body); self.assertIn("30%", body)


class EmailDeliveryTests(unittest.TestCase):
    def test_brand_recipients_empty_and_failure_retry(self):
        from app.models import Base
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db, db.begin():
            user = User(cognito_sub="email-test"); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="Demo", alert_emails=[]); db.add(brand); db.flush()
            db.add(AlertRule(brand_id=brand.id, content_type="comment", enabled=True, growth_percent=50,
                             window_days=1, minimum_current=1))
            alert = Alert(brand_id=brand.id, content_type="comment", mode="window", window_start=now, window_end=now,
                          previous_negative=1, current_negative=2, previous_total=10, current_total=10,
                          growth_percent=50, minimum_current=1, reason="growth_threshold")
            alert.email_status, alert.email_due_at = "pending", now
            db.add(alert); db.flush(); alert_id, brand_id = alert.id, brand.id
        sent = []
        self.assertFalse(notify_alert(engine, alert_id, lambda *args: sent.append(args), "https://example.test"))
        with Session(engine) as db, db.begin():
            self.assertIsNone(db.get(Alert, alert_id).notified_at)
            db.get(Alert, alert_id).email_status, db.get(Alert, alert_id).email_due_at = "pending", now
            db.get(Brand, brand_id).alert_emails = ["one@example.com", "two@example.com"]
        def fail(*args):
            raise ClientError({"Error": {"Code": "Throttling"}}, "SendEmail")
        self.assertFalse(notify_alert(engine, alert_id, fail, "https://example.test", current=now))
        with Session(engine) as db:
            self.assertIsNone(db.get(Alert, alert_id).notified_at)
        self.assertTrue(notify_alert(engine, alert_id, lambda *args: sent.append(args), "https://example.test", current=now + timedelta(minutes=3)))
        self.assertFalse(notify_alert(engine, alert_id, lambda *args: sent.append(args), "https://example.test"))
        self.assertEqual(sent[0][2], ["one@example.com", "two@example.com"])
        self.assertEqual(len(sent), 1)
        engine.dispose()

    def test_ses_uses_bcc(self):
        from app.demo_alerts import email_publisher
        class SES:
            def send_email(self, **kwargs):
                calls.append(kwargs)
        calls = []
        with patch.dict(os.environ, {"ALERT_SENDER_EMAIL": "sender@example.com"}), patch("boto3.client", return_value=SES()):
            email_publisher()("subject", "body", ["a@example.com", "b@example.com"])
        self.assertEqual(calls[0]["Destination"], {"BccAddresses": ["a@example.com", "b@example.com"]})
        self.assertEqual(calls[0]["Source"], "sender@example.com")


class ServerPrefixTests(unittest.TestCase):
    def test_prefix_is_stripped_for_api_paths_only(self):
        seen = []

        async def fake(scope, receive, send):
            seen.append(scope["path"])
        with patch.dict(os.environ, {"API_PATH_PREFIX": "/api"}):
            import importlib
            import app.server as server
            server = importlib.reload(server)
            with patch.object(server, "api", fake):
                for path in ("/api/brands", "/api", "/health", "/apis"):
                    asyncio.run(server.app({"type": "http", "path": path}, None, None))
        self.assertEqual(seen, ["/brands", "/", "/health", "/apis"])


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class DemoAlertFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"])

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def make_brand(self, rule=True):
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="KFCC", alert_emails=["one@example.com", "two@example.com"]); db.add(brand); db.flush()
            db.add(TrackingConfig(brand_id=brand.id, frequency="daily", run_time="08:00",
                                  timezone="Asia/Ho_Chi_Minh", post_limit=1, active=True))
            db.add(BrandKeyword(brand_id=brand.id, keyword="KFCC"))
            db.add(BrandSource(brand_id=brand.id, source="tiktok"))
            if rule:
                db.add(AlertRule(brand_id=brand.id, content_type="comment", enabled=True, growth_percent=50,
                                 window_days=1, minimum_current=10, absolute_threshold=None))
            return brand.id

    def environment(self, brand_id, session_id, expiry):
        return {"DEMO_STREAM_ENABLED": "true", "DEMO_BRAND_ID": str(brand_id), "DEMO_SESSION_ID": str(session_id),
                "DEMO_MAX_BATCHES": "3", "DEMO_AUTO_BATCHES": "2", "DEMO_INTERVAL_MINUTES": "1",
                "DEMO_EXPIRES_AT": expiry.isoformat(), "WORKER_QUEUE_URL": "queue", "BRAND_SCHEDULER_ENABLED": "false",
                "ALERT_SENDER_EMAIL": "sender@example.com", "APP_BASE_URL": "https://demo.example"}

    def run_batch(self, brand_id, session_id, expiry, current, manual=False):
        from app.demo_scheduler import enqueue_demo
        from app.lambda_worker import handle_queue
        run_id = enqueue_demo(self.engine, brand_id, session_id, 3, expiry, current, 1, auto_batches=2, manual=manual)
        self.assertIsNotNone(run_id)
        with Session(self.engine) as db:
            event_id = db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == run_id))
        record = [{"messageId": str(run_id), "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}]
        self.assertEqual(handle_queue(self.engine, record), {"batchItemFailures": []})
        return run_id

    def test_full_scenario_alerts_once_and_emails_once(self):
        from app.demo_scheduler import enqueue_demo
        brand_id, session_id = self.make_brand(), uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=30)
        sent = []
        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.lambda_worker.provider", side_effect=AssertionError("Không được gọi Firecrawl")), \
             patch("app.demo_alerts.email_publisher", return_value=lambda subject, body, recipients: sent.append((subject, body, recipients))):
            first = self.run_batch(brand_id, session_id, expiry, current)
            # Đợt 2 phải chờ đủ khoảng cách; đợt thủ công bị từ chối khi chưa xong đợt tự động.
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 3, expiry, current + timedelta(seconds=30), 1, auto_batches=2))
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 3, expiry, current, 1, auto_batches=2, manual=True))
            second = self.run_batch(brand_id, session_id, expiry, current + timedelta(minutes=1))
            # Lịch tự động dừng sau đợt 2; đợt tích cực chỉ chạy khi người vận hành yêu cầu.
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 3, expiry, current + timedelta(minutes=5), 1, auto_batches=2))
            third = self.run_batch(brand_id, session_id, expiry, current + timedelta(minutes=2), manual=True)
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 3, expiry, current + timedelta(minutes=9), 1, auto_batches=2, manual=True))
        with Session(self.engine) as db:
            alerts = db.scalars(select(Alert).where(Alert.brand_id == brand_id)).all()
            self.assertEqual(len(alerts), 1)
            alert = alerts[0]
            self.assertEqual((alert.mode, alert.run_id), ("run", second))
            self.assertEqual((alert.previous_negative, alert.previous_total, alert.current_negative, alert.current_total), (20, 100, 60, 200))
            self.assertIsNotNone(alert.notified_at)
            self.assertEqual(db.scalar(select(func.count()).select_from(SentimentResult).where(SentimentResult.brand_id == brand_id)), 300)
            self.assertEqual(set(db.scalars(select(SentimentResult.model_id).where(SentimentResult.brand_id == brand_id))), {"demo-fixture-labels"})
            self.assertTrue(all(work.status == "complete" for work in db.scalars(select(SentimentWork).where(SentimentWork.run_id.in_([first, second, third])))))
            timeline = sentiment_timeline(db, brand_id)["points"]
        self.assertEqual([(p["negative"], p["total"]) for p in timeline], [(20, 100), (60, 200), (65, 300)])
        self.assertEqual([p["alert_id"] is not None for p in timeline], [False, True, False])
        self.assertEqual([p["new_comments"] for p in timeline], [100, 100, 100])
        self.assertEqual([p["evaluation_status"] for p in timeline], ["insufficient_data", "triggered", "not_triggered"])
        self.assertEqual(timeline[0]["evaluation_reason"], "baseline")
        with patch("app.demo_alerts.MAX_TIMELINE_ROWS", 1), patch("app.demo_alerts.MAX_TIMELINE_RUNS", 2):
            with Session(self.engine) as db:
                limited = sentiment_timeline(db, brand_id)
        self.assertTrue(limited["truncated"])
        self.assertTrue(limited["history_limited"])
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][2], ["one@example.com", "two@example.com"])
        self.assertIn(str(alert.id), sent[0][1])

    def test_re_evaluation_and_retry_do_not_duplicate(self):
        from app.demo_alerts import evaluate_run_alert, process_demo_run
        brand_id, session_id = self.make_brand(), uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=30)
        sent = []
        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.demo_alerts.email_publisher", return_value=None):
            self.run_batch(brand_id, session_id, expiry, current)
            second = self.run_batch(brand_id, session_id, expiry, current + timedelta(minutes=1))
        with Session(self.engine) as db:
            alert = db.scalar(select(Alert).where(Alert.run_id == second))
            self.assertIsNone(alert.notified_at)
        # SES từ chối vì quá tốc độ. Việc giữ lịch thử lại qua lần gọi worker tiếp theo.
        def broken(subject, body, recipients):
            raise ClientError({"Error": {"Code": "Throttling"}}, "SendEmail")
        self.assertFalse(notify_alert(self.engine, alert.id, broken, "https://demo.example"))
        from app.demo_alerts import deliver_pending_alert_emails
        with Session(self.engine) as db, db.begin():
            job = db.get(Alert, alert.id)
            self.assertEqual((job.email_status, job.email_attempts), ("pending", 1))
            job.email_due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        def publish(subject, body, recipients):
            # Một worker khác đến khi công việc đang ở trạng thái sending.
            self.assertFalse(notify_alert(self.engine, alert.id, publish, "https://demo.example"))
            sent.append(body)

        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.demo_alerts.email_publisher", return_value=publish):
            deliver_pending_alert_emails(self.engine)
        self.assertFalse(notify_alert(self.engine, alert.id, lambda s, b, recipients: sent.append(b), "https://demo.example"))
        again = evaluate_run_alert(self.engine, second)
        self.assertEqual((again["status"], again["created"]), ("triggered", False))
        with patch.dict(os.environ, {"ALERT_SENDER_EMAIL": "", "APP_BASE_URL": ""}):
            process_demo_run(self.engine, second)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Alert).where(Alert.brand_id == brand_id)), 1)
        self.assertEqual(sum(f"&alert={alert.id}" in body for body in sent), 1)

    def test_interrupted_email_has_unknown_status_and_is_not_resent(self):
        from app.demo_alerts import deliver_pending_alert_emails
        brand_id, session_id = self.make_brand(), uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=30)
        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.demo_alerts.email_publisher", return_value=None):
            self.run_batch(brand_id, session_id, expiry, current)
            run_id = self.run_batch(brand_id, session_id, expiry, current + timedelta(minutes=1))
        with Session(self.engine) as db, db.begin():
            job = db.scalar(select(Alert).where(Alert.run_id == run_id))
            alert_id = job.id
            job.email_status, job.email_attempts, job.email_due_at = "sending", 1, current
        sent = []
        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.demo_alerts.email_publisher", return_value=lambda s, b, recipients: sent.append(b)):
            deliver_pending_alert_emails(self.engine)
        self.assertFalse(any(f"&alert={alert_id}" in body for body in sent))
        with Session(self.engine) as db:
            job = db.get(Alert, alert_id)
            self.assertEqual((job.email_status, job.notified_at), ("unknown", None))

    def test_disabled_rule_and_baseline_do_not_alert(self):
        from app.demo_alerts import evaluate_run_alert
        brand_id, session_id = self.make_brand(rule=False), uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=30)
        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.demo_alerts.email_publisher", return_value=None):
            first = self.run_batch(brand_id, session_id, expiry, current)
            second = self.run_batch(brand_id, session_id, expiry, current + timedelta(minutes=1))
        self.assertEqual(evaluate_run_alert(self.engine, second)["status"], "disabled")
        with Session(self.engine) as db, db.begin():
            db.add(AlertRule(brand_id=brand_id, content_type="comment", enabled=True, growth_percent=50,
                             window_days=1, minimum_current=10, absolute_threshold=None))
        with Session(self.engine) as db:
            points = sentiment_timeline(db, brand_id)["points"]
            self.assertEqual([point["evaluation_status"] for point in points], ["disabled", "disabled"])
        self.assertEqual(evaluate_run_alert(self.engine, first)["reason"], "baseline")
        self.assertEqual(evaluate_run_alert(self.engine, second)["status"], "triggered")

    def test_non_demo_run_is_not_applicable(self):
        from app.demo_alerts import evaluate_run_alert, label_demo_run
        brand_id = self.make_brand()
        with Session(self.engine) as db, db.begin():
            run = TrackingRun(brand_id=brand_id, status="success", config_snapshot={"keywords": ["x"]},
                              finished_at=datetime.now(timezone.utc))
            db.add(run); db.flush(); run_id = run.id
        self.assertEqual(evaluate_run_alert(self.engine, run_id)["status"], "not_applicable")
        with self.assertRaises(ValueError):
            label_demo_run(self.engine, run_id)

    def test_api_timeline_and_latest_run_evaluation(self):
        from fastapi.testclient import TestClient
        from app.auth import current_subject
        from app.database import session
        from app.main import app
        brand_id, session_id = self.make_brand(), uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=30)
        with patch.dict(os.environ, self.environment(brand_id, session_id, expiry)), \
             patch("app.demo_alerts.email_publisher", return_value=None):
            self.run_batch(brand_id, session_id, expiry, current)
            self.run_batch(brand_id, session_id, expiry, current + timedelta(minutes=1))
        with Session(self.engine) as db:
            owner = db.scalar(select(User.cognito_sub).join(Brand, Brand.owner_id == User.id).where(Brand.id == brand_id))

        def database():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[session] = database
        try:
            app.dependency_overrides[current_subject] = lambda: owner
            client = TestClient(app)
            timeline = client.get(f"/brands/{brand_id}/sentiment-timeline").json()
            self.assertEqual([(p["negative"], p["total"]) for p in timeline["points"]], [(20, 100), (60, 200)])
            result = client.post(f"/brands/{brand_id}/alerts/evaluate-latest-run").json()
            self.assertEqual((result["status"], result["current_total"]), ("triggered", 200))
            alerts = client.get(f"/brands/{brand_id}/alerts").json()
            self.assertEqual(len(alerts), 1)
            self.assertEqual((alerts[0]["mode"], alerts[0]["previous_total"], alerts[0]["current_total"]), ("run", 100, 200))
            alert_id = alerts[0]["id"]
            self.assertEqual(client.get(f"/brands/{brand_id}").json()["name"], "KFCC")
            self.assertEqual(client.get(f"/brands/{brand_id}/alerts/{alert_id}").json(), alerts[0])
            self.assertEqual(client.get(f"/brands/{brand_id}/alerts/{uuid4()}").status_code, 404)
            other_brand = self.make_brand()
            with Session(self.engine) as db, db.begin():
                db.get(Brand, other_brand).owner_id = db.get(Brand, brand_id).owner_id
            self.assertEqual(client.get(f"/brands/{other_brand}/alerts/{alert_id}").status_code, 404)
            app.dependency_overrides[current_subject] = lambda: str(uuid4())
            self.assertEqual(client.get(f"/brands/{brand_id}").status_code, 404)
            self.assertEqual(client.get(f"/brands/{brand_id}/alerts/{alert_id}").status_code, 404)
            app.dependency_overrides[current_subject] = lambda: owner
            # Xóa nhãn hàng vẫn xóa được cảnh báo gắn phiên.
            self.assertEqual(client.delete(f"/brands/{brand_id}").status_code, 200)
            app.dependency_overrides[current_subject] = lambda: str(uuid4())
            self.assertEqual(client.get(f"/brands/{brand_id}/sentiment-timeline").status_code, 404)
        finally:
            app.dependency_overrides.clear()

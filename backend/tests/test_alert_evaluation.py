"""So sánh cảnh báo bằng dữ liệu PostgreSQL và các phiên fixture."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.alert_evaluation import collect_comparison
from app.models import Brand, Comment, Post, RunCommentMatch, RunPostMatch, SentimentResult, TrackingAttempt, TrackingRun, User
from app.sentiment import content_hash
from app.demo_history import seed_history

UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)
MIDDLE = START + timedelta(days=1)
END = MIDDLE + timedelta(days=1)


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"])

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def fixture(self, before=10, after=15):
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="comparison"); db.add(brand); db.flush()
            ids = []
            for index, count in enumerate((before, after)):
                slot = START + timedelta(days=index, hours=8)
                snapshot = {"keywords": ["coffee"], "sources": ["tiktok"], "frequency": "daily",
                            "runTime": "08:00", "timezone": "UTC", "postLimit": 50,
                            "search_pages": 1, "comment_pages": 1, "scheduled_for": slot.isoformat()}
                run = TrackingRun(brand_id=brand.id, queued_at=slot + timedelta(minutes=1), started_at=slot + timedelta(minutes=1),
                                  finished_at=slot + timedelta(minutes=5), status="success", config_snapshot=snapshot)
                db.add(run); db.flush(); ids.append(run.id)
                db.add(TrackingAttempt(run_id=run.id, source="tiktok", keyword="coffee", status="success", result_count=count))
                for item in range(count):
                    content = f"negative {index} {item}"
                    post = Post(brand_id=brand.id, source="tiktok", source_id=str(uuid4()), url="https://example.test",
                                content=content, first_seen_at=slot + timedelta(minutes=2))
                    db.add(post); db.flush()
                    db.add(RunPostMatch(brand_id=brand.id, run_id=run.id, post_id=post.id,
                                        observed_at=slot + timedelta(minutes=2), content_hash=content_hash(content)))
                    db.add(SentimentResult(brand_id=brand.id, post_id=post.id, label="negative", model_id="model-v1",
                                           content_hash=content_hash(content), classified_at=slot + timedelta(minutes=3)))
            return brand.id, ids

    def comparison(self, brand):
        return collect_comparison(self.engine, brand, "post", START, MIDDLE, END)

    def test_demo_history_triggers_real_alert_once_and_is_idempotent(self):
        from app.alert_evaluation import evaluate_alert_rule
        from app.models import Alert, AlertRule
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="Mây Tea demo"); db.add(brand); db.flush()
            brand_id = brand.id
            db.add(AlertRule(brand_id=brand.id, content_type="comment", enabled=True, growth_percent=50,
                             window_days=1, minimum_current=1, absolute_threshold=None))
        session_id = uuid4()
        result = seed_history(self.engine, brand_id, session_id)
        self.assertEqual(result["status"], "seeded")
        self.assertEqual(seed_history(self.engine, brand_id, session_id)["status"], "already_seeded")
        end = datetime.fromisoformat(result["window_end"])
        first = evaluate_alert_rule(self.engine, brand_id, "comment", end)
        second = evaluate_alert_rule(self.engine, brand_id, "comment", end)
        self.assertEqual((first["status"], first["previous_negative"], first["current_negative"]), ("triggered", 10, 15))
        self.assertEqual(first["alert"].id, second["alert"].id)
        with Session(self.engine) as db:
            self.assertEqual(len(db.scalars(select(Alert).where(Alert.brand_id == brand_id)).all()), 1)

    def test_counts_are_unique_and_support_growth_threshold(self):
        brand, _ = self.fixture()
        result = self.comparison(brand)
        self.assertEqual((result.status, result.previous_negative, result.current_negative), ("comparable", 10, 15))
        from app.alert_rules import evaluate_increase
        from decimal import Decimal
        self.assertEqual(evaluate_increase(result.previous_negative, result.current_negative, growth_percent=Decimal(50),
                                           minimum_current=5, comparable=True, fully_classified=True).status, "triggered")

    def test_missing_attempt_scope_or_schedule_rejects(self):
        for failure in ("attempt", "scope", "schedule"):
            brand, runs = self.fixture(before=1, after=1)
            with Session(self.engine) as db, db.begin():
                run = db.get(TrackingRun, runs[1])
                if failure == "attempt":
                    db.execute(delete(TrackingAttempt).where(TrackingAttempt.run_id == run.id))
                elif failure == "scope":
                    run.config_snapshot = {**run.config_snapshot, "postLimit": 1}
                else:
                    run.config_snapshot = {key: value for key, value in run.config_snapshot.items() if key != "scheduled_for"}
            self.assertEqual(self.comparison(brand).status, "insufficient_data")

    def test_changed_content_missing_label_or_identity_rejects(self):
        for failure in ("content", "label", "identity", "time", "version"):
            brand, runs = self.fixture(before=1, after=1)
            with Session(self.engine) as db, db.begin():
                match = db.scalar(select(RunPostMatch).where(RunPostMatch.run_id == runs[1]))
                post = db.get(Post, match.post_id)
                result = db.scalar(select(SentimentResult).where(SentimentResult.post_id == post.id))
                if failure == "content": post.content = "changed"
                elif failure == "label": result.label = "unknown"
                elif failure == "identity": post.source_id = None
                elif failure == "time": match.observed_at = None
                else: result.classifier_version = "old-prompt"
            self.assertEqual(self.comparison(brand).status, "insufficient_data")

    def test_empty_window_requires_a_successful_scheduled_run(self):
        brand, _ = self.fixture(before=0, after=1)
        result = self.comparison(brand)
        self.assertEqual((result.previous_negative, result.current_negative), (0, 1))
        self.assertEqual(collect_comparison(self.engine, uuid4(), "post", START, MIDDLE, END).status, "insufficient_data")

    def test_same_post_seen_twice_is_counted_only_in_first_window(self):
        brand, runs = self.fixture(before=1, after=1)
        with Session(self.engine) as db, db.begin():
            first = db.scalar(select(RunPostMatch).where(RunPostMatch.run_id == runs[0]))
            db.add(RunPostMatch(brand_id=brand, run_id=runs[1], post_id=first.post_id,
                                observed_at=MIDDLE + timedelta(hours=9), content_hash=first.content_hash))
        result = self.comparison(brand)
        self.assertEqual((result.previous_negative, result.current_negative), (1, 1))

    def test_late_or_failed_run_is_not_comparable(self):
        for mode in ("late", "failed"):
            brand, runs = self.fixture(before=1, after=1)
            with Session(self.engine) as db, db.begin():
                run = db.get(TrackingRun, runs[1])
                if mode == "late": run.queued_at += timedelta(hours=1)
                else: run.status = "partial"
            self.assertEqual(self.comparison(brand).reason, "failed_or_late_run")

    def test_comments_are_counted_by_their_first_observation(self):
        brand, runs = self.fixture(before=1, after=1)
        with Session(self.engine) as db, db.begin():
            for run_id in runs:
                match = db.scalar(select(RunPostMatch).where(RunPostMatch.run_id == run_id))
                comment = Comment(brand_id=brand, post_id=match.post_id, source_id=str(uuid4()), content="bad")
                db.add(comment); db.flush()
                db.add(RunCommentMatch(brand_id=brand, run_id=run_id, post_id=match.post_id, comment_id=comment.id,
                                       observed_at=match.observed_at, content_hash=content_hash("bad")))
                db.add(SentimentResult(brand_id=brand, comment_id=comment.id, label="negative", model_id="model-v1",
                                       content_hash=content_hash("bad"), classified_at=match.observed_at))
        result = collect_comparison(self.engine, brand, "comment", START, MIDDLE, END)
        self.assertEqual((result.status, result.previous_negative, result.current_negative), ("comparable", 1, 1))

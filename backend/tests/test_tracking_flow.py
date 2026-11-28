"""Luồng tracking với provider giả và PostgreSQL thử nghiệm."""
import os
import io
import time
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4
from unittest.mock import Mock, patch

from sqlalchemy import Date, cast, create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.firecrawl import FirecrawlTikTok, ProviderError, reserve_daily_credits
from app.models import (AttemptPostMatch, Brand, BrandKeyword, BrandSource, Comment, EngagementSnapshot, FirecrawlCreditReservation, Post,
                        RunCommentMatch, RunPostMatch, TrackingAttempt, TrackingConfig, TrackingOutbox, TrackingRun, User)
from app.outbox import count_exhausted, publish_pending
from app.lambda_worker import handle_queue, provider_for_run
from app.tracking import (LeaseHeartbeat, RunNotActive, RunNotQueued, ensure_active, finish, mark_stale,
                          prepare, run_once, run_queued, save_post)
from app.adapters.tiktok import post_record
from app.sentiment import content_hash
from datetime import datetime, timedelta, timezone
from app.worker import work_once
from app.demo_stream import DemoProvider
from app.demo_scheduler import enqueue_demo


class FakeProvider:
    def __init__(self, likes=5, failed_comments=False, empty=False):
        self.likes, self.failed_comments, self.empty = likes, failed_comments, empty
        self.calls = []

    def search(self, keyword):
        self.calls.append(("search", keyword))
        if self.empty:
            return []
        return [{"aweme_id": "v1", "url": "https://www.tiktok.com/@demo/video/1", "desc": "sample",
                 "create_time": int(time.time()), "statistics": {"digg_count": self.likes, "comment_count": 1}}]

    def comments(self, url):
        self.calls.append(("comments", url))
        if self.failed_comments:
            raise ProviderError("network_or_invalid_response")
        return [{"cid": "c1", "text": "sample comment", "digg_count": 2, "user": {"ignored": "personal"}}]


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class TrackingFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(os.environ["TEST_DATABASE_URL"])

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def make_brand(self, sources=("tiktok",), keywords=("one", "two")):
        with Session(self.engine) as db, db.begin():
            user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
            brand = Brand(owner_id=user.id, name="Fixture"); db.add(brand); db.flush()
            db.add(TrackingConfig(brand_id=brand.id, frequency="daily", run_time="08:00",
                                  timezone="Asia/Ho_Chi_Minh", post_limit=5, active=True))
            db.add_all([BrandKeyword(brand_id=brand.id, keyword=k) for k in keywords])
            db.add_all([BrandSource(brand_id=brand.id, source=s) for s in sources])
            return brand.id

    def test_demo_runs_store_distinct_simulated_sources(self):
        brand_id = self.make_brand(keywords=("KFCC",))
        first_id, first_status = run_once(self.engine, brand_id, DemoProvider("batch1", 3))
        second_id, second_status = run_once(self.engine, brand_id, DemoProvider("batch2", 4))
        self.assertEqual((first_status, second_status), ("success", "success"))
        with Session(self.engine) as db:
            posts = db.scalars(select(Post).where(Post.brand_id == brand_id)).all()
            comments = db.scalars(select(Comment).where(Comment.brand_id == brand_id)).all()
            attempts = db.scalars(select(TrackingAttempt).where(TrackingAttempt.run_id.in_([first_id, second_id]))).all()
            self.assertEqual(len(posts), 2)
            self.assertEqual(len(comments), 7)
            self.assertTrue(all(post.source == "demo" and post.url.startswith("https://example.invalid/") for post in posts))
            self.assertTrue(all("DỮ LIỆU GIẢ" in comment.content for comment in comments))
            self.assertTrue(all(attempt.source == "demo" for attempt in attempts))

    def test_demo_scheduler_queue_is_bounded_and_uses_simulated_provider(self):
        brand_id = self.make_brand(keywords=("KFCC",))
        session_id = uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=10)
        environment = {"DEMO_STREAM_ENABLED": "true", "DEMO_BRAND_ID": str(brand_id),
                       "DEMO_SESSION_ID": str(session_id), "DEMO_MAX_BATCHES": "1",
                       "DEMO_EXPIRES_AT": expiry.isoformat(), "WORKER_QUEUE_URL": "queue",
                       "BRAND_SCHEDULER_ENABLED": "false"}
        with patch.dict(os.environ, environment), patch("app.lambda_worker.provider", side_effect=AssertionError("Không được gọi Firecrawl")):
            run_id = enqueue_demo(self.engine, brand_id, session_id, 1, expiry, current)
            self.assertIsNotNone(run_id)
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 1, expiry, current))
            with Session(self.engine) as db:
                event_id = db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == run_id))
            records = [{"messageId": "demo", "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}]
            self.assertEqual(handle_queue(self.engine, records), {"batchItemFailures": []})
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 1, expiry, current))
            with Session(self.engine) as db:
                self.assertEqual(db.get(TrackingRun, run_id).status, "success")
                self.assertEqual(db.scalar(select(Post.source).where(Post.brand_id == brand_id)), "demo")
        self.assertIsNone(enqueue_demo(self.engine, brand_id, uuid4(), 1, current, current))
        with patch.dict(os.environ, {"DEMO_STREAM_ENABLED": "false"}), \
             patch("app.lambda_worker.provider", side_effect=AssertionError("Không được gọi Firecrawl")):
            with self.assertRaises(ValueError):
                provider_for_run(self.engine, run_id)

    def test_demo_queue_later_batch_changes_the_scenario(self):
        brand_id = self.make_brand(keywords=("KFCC",))
        session_id = uuid4()
        current = datetime.now(timezone.utc)
        expiry = current + timedelta(minutes=10)
        environment = {"DEMO_STREAM_ENABLED": "true", "DEMO_BRAND_ID": str(brand_id),
                       "DEMO_SESSION_ID": str(session_id), "DEMO_MAX_BATCHES": "2",
                       "DEMO_EXPIRES_AT": expiry.isoformat(), "WORKER_QUEUE_URL": "queue",
                       "BRAND_SCHEDULER_ENABLED": "false"}
        with patch.dict(os.environ, environment):
            for number in (1, 2):
                if number == 2:
                    self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 2, expiry, current + timedelta(seconds=119), interval_minutes=2))
                    current += timedelta(minutes=2)
                run_id = enqueue_demo(self.engine, brand_id, session_id, 2, expiry, current, interval_minutes=2)
                with Session(self.engine) as db:
                    run = db.get(TrackingRun, run_id)
                    self.assertEqual(run.config_snapshot["demo_batch"], number)
                    event_id = db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == run_id))
                records = [{"messageId": str(number), "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}]
                self.assertEqual(handle_queue(self.engine, records), {"batchItemFailures": []})
            self.assertIsNone(enqueue_demo(self.engine, brand_id, session_id, 2, expiry, current))

    def test_same_post_across_keywords_and_runs_does_not_duplicate_content(self):
        brand_id = self.make_brand()
        first_provider = FakeProvider(likes=5)
        first_id, first_status = run_once(self.engine, brand_id, first_provider)
        second_id, second_status = run_once(self.engine, brand_id, FakeProvider(likes=9))
        self.assertEqual((first_status, second_status), ("success", "success"))
        self.assertEqual(len([call for call in first_provider.calls if call[0] == "comments"]), 1)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Comment).where(Comment.brand_id == brand_id)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(RunPostMatch).where(RunPostMatch.brand_id == brand_id)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(RunCommentMatch).where(RunCommentMatch.brand_id == brand_id)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(TrackingAttempt).where(TrackingAttempt.run_id == first_id)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(AttemptPostMatch).where(AttemptPostMatch.run_id == first_id)), 2)
            likes = db.scalars(select(EngagementSnapshot.likes).where(EngagementSnapshot.brand_id == brand_id,
                               EngagementSnapshot.post_id.is_not(None)).order_by(EngagementSnapshot.captured_at)).all()
            self.assertEqual(likes, [5, 9])
            self.assertIsNotNone(db.get(TrackingRun, second_id).finished_at)
            post_matches = db.scalars(select(RunPostMatch).where(RunPostMatch.brand_id == brand_id)).all()
            comment_matches = db.scalars(select(RunCommentMatch).where(RunCommentMatch.brand_id == brand_id)).all()
            self.assertTrue(all(row.observed_at is not None and row.content_hash == content_hash("sample") for row in post_matches))
            self.assertTrue(all(row.observed_at is not None and row.content_hash == content_hash("sample comment") for row in comment_matches))

    def test_each_run_preserves_observed_content_version(self):
        brand_id = self.make_brand(keywords=("one",))
        class ChangedProvider(FakeProvider):
            def search(self, keyword):
                rows = super().search(keyword)
                rows[0]["desc"] = "changed post"
                return rows
            def comments(self, url):
                return [{"cid": "c1", "text": "changed comment"}]
        first, _ = run_once(self.engine, brand_id, FakeProvider())
        second, _ = run_once(self.engine, brand_id, ChangedProvider())
        with Session(self.engine) as db:
            posts = {row.run_id: row for row in db.scalars(select(RunPostMatch).where(RunPostMatch.brand_id == brand_id))}
            comments = {row.run_id: row for row in db.scalars(select(RunCommentMatch).where(RunCommentMatch.brand_id == brand_id))}
            self.assertEqual((posts[first].content_hash, posts[second].content_hash), (content_hash("sample"), content_hash("changed post")))
            self.assertEqual((comments[first].content_hash, comments[second].content_hash), (content_hash("sample comment"), content_hash("changed comment")))
            self.assertLessEqual(posts[first].observed_at, posts[second].observed_at)

    def test_empty_partial_failed_and_running_lock(self):
        brand_id = self.make_brand(sources=("tiktok", "reddit"), keywords=("one",))
        run_id, status = run_once(self.engine, brand_id, FakeProvider(empty=True))
        self.assertEqual(status, "partial")
        with Session(self.engine) as db:
            attempts = db.scalars(select(TrackingAttempt).where(TrackingAttempt.run_id == run_id).order_by(TrackingAttempt.source)).all()
            self.assertEqual([(x.source, x.status, x.error_code) for x in attempts],
                             [("reddit", "failed", "unsupported_source"), ("tiktok", "empty", None)])
        brand_id = self.make_brand(keywords=("one",))
        run_id, status = run_once(self.engine, brand_id, FakeProvider(failed_comments=True))
        self.assertEqual(status, "failed")
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 1)
            self.assertEqual(db.scalar(select(TrackingAttempt.error_code).where(TrackingAttempt.run_id == run_id)), "network_or_invalid_response")
        brand_id = self.make_brand(keywords=("one",))
        prepare(self.engine, brand_id)
        with self.assertRaises(ValueError):
            prepare(self.engine, brand_id)

    def test_repeated_keyword_match_does_not_copy_comment_without_id(self):
        brand_id = self.make_brand()
        class MissingCommentId(FakeProvider):
            def comments(self, url):
                return [{"text": "sample", "digg_count": 0}]
        run_id, status = run_once(self.engine, brand_id, MissingCommentId())
        self.assertEqual(status, "success")
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Comment).where(Comment.brand_id == brand_id)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(AttemptPostMatch).where(AttemptPostMatch.run_id == run_id)), 2)

    def test_queued_run_can_be_claimed_once_and_uses_snapshot(self):
        brand_id = self.make_brand(keywords=("original",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        with self.assertRaises(ValueError):
            prepare(self.engine, brand_id, queued=True)
        with Session(self.engine) as db, db.begin():
            keyword = db.scalar(select(BrandKeyword).where(BrandKeyword.brand_id == brand_id))
            keyword.keyword = "changed"
        provider = FakeProvider(empty=True)
        self.assertEqual(run_queued(self.engine, run_id, provider), (run_id, "success"))
        self.assertEqual(provider.calls, [("search", "original")])
        with self.assertRaises(ValueError):
            run_queued(self.engine, run_id, FakeProvider())

    def test_run_records_provider_page_limits(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        provider = FakeProvider(empty=True)
        provider.search_pages, provider.comment_pages = 2, 3
        self.assertEqual(run_queued(self.engine, run_id, provider), (run_id, "success"))
        with Session(self.engine) as db:
            snapshot = db.get(TrackingRun, run_id).config_snapshot
            self.assertEqual((snapshot["search_pages"], snapshot["comment_pages"]), (2, 3))

    def test_outbox_retries_send_failure_and_does_not_publish_twice(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        sqs = Mock()
        sqs.send_message.side_effect = [RuntimeError("private detail"), {}]
        self.assertEqual(publish_pending(self.engine, sqs, "queue"), (0, 1))
        with Session(self.engine) as db:
            row = db.scalar(select(TrackingOutbox).where(TrackingOutbox.run_id == run_id))
            self.assertEqual((row.publish_attempts, row.last_error, row.published_at), (1, "queue_send_failed", None))
        self.assertEqual(publish_pending(self.engine, sqs, "queue"), (1, 0))
        self.assertEqual(publish_pending(self.engine, sqs, "queue"), (0, 0))
        self.assertEqual(sqs.send_message.call_count, 2)
        sent = json.loads(sqs.send_message.call_args.kwargs["MessageBody"])
        self.assertEqual(sent["run_id"], str(run_id))
        self.assertEqual(sqs.send_message.call_args_list[0].kwargs["MessageBody"],
                         sqs.send_message.call_args_list[1].kwargs["MessageBody"])
        self.assertEqual(run_queued(self.engine, run_id, FakeProvider(empty=True))[1], "success")
        with self.assertRaises(RunNotQueued):
            run_queued(self.engine, run_id, FakeProvider(empty=True))

    def test_outbox_concurrent_dispatch_holds_one_row_lock(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        entered, release = Event(), Event()
        def send_message(**kwargs):
            entered.set()
            if not release.wait(timeout=10):
                raise RuntimeError("test timeout")
        sqs = Mock(); sqs.send_message.side_effect = send_message
        with ThreadPoolExecutor(max_workers=1) as executor:
            task = executor.submit(publish_pending, self.engine, sqs, "queue")
            self.assertTrue(entered.wait(timeout=10))
            try:
                self.assertEqual(publish_pending(self.engine, sqs, "queue"), (0, 0))
            finally:
                release.set()
            self.assertEqual(task.result(timeout=10), (1, 0))
        self.assertEqual(sqs.send_message.call_count, 1)
        self.assertEqual(run_queued(self.engine, run_id, FakeProvider(empty=True))[1], "success")

    def test_queue_redelivery_reuses_existing_run_without_new_provider_call(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        with Session(self.engine) as db:
            event_id = db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == run_id))
        records = [{"messageId": "test-message", "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}]
        provider = FakeProvider()
        with patch("app.lambda_worker.provider", return_value=provider) as factory, patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(handle_queue(self.engine, records), {"batchItemFailures": []})
            self.assertEqual(handle_queue(self.engine, records), {"batchItemFailures": []})
        factory.assert_called_once()
        self.assertEqual([call[0] for call in provider.calls], ["search", "comments"])
        with Session(self.engine) as db:
            self.assertEqual(db.get(TrackingRun, run_id).status, "success")
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 1)

    def test_queue_concurrent_delivery_is_retried_while_first_worker_runs(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        with Session(self.engine) as db:
            event_id = db.scalar(select(TrackingOutbox.id).where(TrackingOutbox.run_id == run_id))
        records = [{"messageId": "same-message", "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}]
        entered, release = Event(), Event()
        class SlowProvider(FakeProvider):
            def search(self, keyword):
                entered.set()
                if not release.wait(timeout=10):
                    raise RuntimeError("test timeout")
                return super().search(keyword)
        provider = SlowProvider()
        with patch("app.lambda_worker.provider", return_value=provider) as factory, patch("sys.stdout", new_callable=io.StringIO):
            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(handle_queue, self.engine, records)
                self.assertTrue(entered.wait(timeout=10))
                try:
                    self.assertEqual(handle_queue(self.engine, records),
                                     {"batchItemFailures": [{"itemIdentifier": "same-message"}]})
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=10), {"batchItemFailures": []})
            self.assertEqual(handle_queue(self.engine, records), {"batchItemFailures": []})
        factory.assert_called_once()
        self.assertEqual([call[0] for call in provider.calls], ["search", "comments"])

    def test_outbox_send_failure_is_bounded_and_visible(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        sqs = Mock(); sqs.send_message.side_effect = RuntimeError("unavailable")
        self.assertEqual(publish_pending(self.engine, sqs, "queue", max_attempts=2), (0, 1))
        self.assertEqual(publish_pending(self.engine, sqs, "queue", max_attempts=2), (0, 1))
        self.assertEqual(publish_pending(self.engine, sqs, "queue", max_attempts=2), (0, 0))
        self.assertEqual(count_exhausted(self.engine, max_attempts=2), 1)
        with Session(self.engine) as db, db.begin():
            db.get(TrackingRun, run_id).status = "failed"

    def test_daily_credit_reservation_is_atomic_across_workers(self):
        with Session(self.engine) as db, db.begin():
            today = db.scalar(select(cast(func.timezone("UTC", func.now()), Date)))
            db.execute(delete(FirecrawlCreditReservation).where(FirecrawlCreditReservation.day == today))
        barrier = Barrier(6)
        def reserve():
            barrier.wait(timeout=10)
            try:
                reserve_daily_credits(self.engine, 6, 2)
                return "reserved"
            except ProviderError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: reserve(), range(6)))
        self.assertEqual(results.count("reserved"), 3)
        self.assertEqual(results.count("daily_estimated_credit_limit"), 3)
        with Session(self.engine) as db:
            row = db.get(FirecrawlCreditReservation, today)
            self.assertEqual((row.reserved, row.daily_limit, row.unit_estimate), (6, 6, 2))
        with self.assertRaises(ProviderError):
            reserve_daily_credits(self.engine, 8, 2)
        with self.assertRaises(ProviderError):
            reserve_daily_credits(self.engine, 6, 1)

    def test_pause_prevents_queued_run_from_starting(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        with Session(self.engine) as db, db.begin():
            db.get(TrackingConfig, brand_id).active = False
        provider = FakeProvider()
        self.assertEqual(run_queued(self.engine, run_id, provider), (run_id, "skipped"))
        self.assertEqual(provider.calls, [])
        with Session(self.engine) as db:
            self.assertEqual(db.get(TrackingRun, run_id).error_code, "tracking_paused")

    def test_worker_picks_queued_run_without_polluting_output(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        self.assertEqual(work_once(self.engine, lambda: FakeProvider(empty=True)), (run_id, "success"))
        self.assertIsNone(work_once(self.engine, lambda: FakeProvider()))

    def test_two_workers_cannot_claim_same_run(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        barrier = Barrier(2)
        def try_claim():
            barrier.wait(timeout=10)
            try:
                return run_queued(self.engine, run_id, FakeProvider(empty=True))[1]
            except RunNotQueued:
                return "already_claimed"
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: try_claim(), range(2)))
        self.assertCountEqual(statuses, ["success", "already_claimed"])

    def test_two_requests_cannot_create_parallel_runs_for_brand(self):
        brand_id = self.make_brand(keywords=("one",))
        barrier = Barrier(2)
        def try_enqueue():
            barrier.wait(timeout=10)
            try:
                prepare(self.engine, brand_id, queued=True)
                return "queued"
            except ValueError:
                return "already_active"
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: try_enqueue(), range(2)))
        self.assertCountEqual(statuses, ["queued", "already_active"])
        # Tránh để phiên chờ ảnh hưởng đến kiểm thử worker khác.
        with Session(self.engine) as db, db.begin():
            run = db.scalar(select(TrackingRun).where(TrackingRun.brand_id == brand_id))
            run.status = "failed"

    def test_call_budget_failure_preserves_post_and_marks_attempt(self):
        brand_id = self.make_brand(keywords=("one",))
        class BudgetProvider(FakeProvider):
            def comments(self, url):
                raise ProviderError("call_limit")
        run_id, status = run_once(self.engine, brand_id, BudgetProvider())
        self.assertEqual(status, "failed")
        with Session(self.engine) as db:
            attempt = db.scalar(select(TrackingAttempt).where(TrackingAttempt.run_id == run_id))
            self.assertEqual((attempt.status, attempt.result_count, attempt.error_code), ("failed", 1, "call_limit"))
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 1)

    def test_stale_worker_cannot_write_or_overwrite_failed_run(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id)
        with Session(self.engine) as db, db.begin():
            run = db.get(TrackingRun, run_id)
            lease_token = run.lease_token
            run.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        sample = post_record({"aweme_id": "v1", "url": "https://tiktok.com/@test/video/1", "statistics": {}})
        # Lease hết hạn đã chặn ghi, ngay cả trước khi bộ quét đánh dấu thất bại.
        with self.assertRaises(RunNotActive):
            save_post(self.engine, run_id, brand_id, sample, [], lease_token)
        self.assertEqual(mark_stale(self.engine, 30), 1)
        with self.assertRaises(RunNotActive):
            save_post(self.engine, run_id, brand_id, sample, [], lease_token)
        with self.assertRaises(RunNotActive):
            finish(self.engine, run_id, "success", lease_token)
        with Session(self.engine) as db:
            run = db.get(TrackingRun, run_id)
            self.assertEqual((run.status, run.error_code), ("failed", "worker_timeout"))
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 0)
        with self.assertRaises(ValueError):
            mark_stale(self.engine, 1)

    def test_heartbeat_renews_in_background_and_reports_loss(self):
        called = Event()
        with patch("app.tracking.ensure_active", side_effect=lambda *args: called.set()):
            heartbeat = LeaseHeartbeat("db", uuid4(), uuid4(), uuid4(), interval_seconds=0.01).start()
            self.assertTrue(called.wait(timeout=1))
            heartbeat.check()
            heartbeat.stop()
        lost = Event()
        def fail(*args):
            lost.set()
            raise RunNotActive("lost")
        with patch("app.tracking.ensure_active", side_effect=fail):
            heartbeat = LeaseHeartbeat("db", uuid4(), uuid4(), uuid4(), interval_seconds=0.01).start()
            self.assertTrue(lost.wait(timeout=1))
            with self.assertRaises(RunNotActive):
                heartbeat.check()
            heartbeat.stop()

    def test_lease_duration_configuration_is_bounded(self):
        from app.tracking import lease_duration
        with patch.dict(os.environ, {"WORKER_LEASE_SECONDS": "30"}):
            self.assertEqual(lease_duration(), timedelta(seconds=30))
        for value in ("29", "3601"):
            with self.subTest(value=value), patch.dict(os.environ, {"WORKER_LEASE_SECONDS": value}):
                with self.assertRaises(ValueError):
                    lease_duration()
    def test_stale_run_is_requeued_once_when_enabled(self):
        brand_id = self.make_brand(keywords=("one",))
        original_id, _ = prepare(self.engine, brand_id)
        with Session(self.engine) as db, db.begin():
            db.get(TrackingRun, original_id).lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertEqual(mark_stale(self.engine, 30, requeue=True), 1)
        with Session(self.engine) as db:
            replacement = db.scalar(select(TrackingRun).where(TrackingRun.brand_id == brand_id,
                                    TrackingRun.status == "queued"))
            self.assertIsNotNone(replacement)
            self.assertEqual(replacement.config_snapshot["recovery_attempt"], 1)
            self.assertEqual(replacement.config_snapshot["recovered_from"], str(original_id))
            self.assertIsNotNone(db.scalar(select(TrackingOutbox).where(TrackingOutbox.run_id == replacement.id)))
            replacement_id = replacement.id
        with Session(self.engine) as db, db.begin():
            replacement = db.get(TrackingRun, replacement_id)
            replacement.status = "running"
            replacement.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
            replacement.lease_token = uuid4()
            replacement.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertEqual(mark_stale(self.engine, 30, requeue=True), 1)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(TrackingRun)
                                       .where(TrackingRun.brand_id == brand_id)), 2)

    def test_lease_owner_is_required_and_renewed_before_external_call(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id)
        sample = post_record({"aweme_id": "v1", "url": "https://tiktok.com/@test/video/1", "statistics": {}})
        with Session(self.engine) as db, db.begin():
            run = db.get(TrackingRun, run_id)
            lease_token = run.lease_token
            run.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=5)
        with self.assertRaises(RunNotActive):
            save_post(self.engine, run_id, brand_id, sample, [], uuid4())
        ensure_active(self.engine, run_id, brand_id, lease_token)
        with Session(self.engine) as db:
            self.assertGreater(db.get(TrackingRun, run_id).lease_expires_at,
                               datetime.now(timezone.utc) + timedelta(minutes=9))
        finish(self.engine, run_id, "success", lease_token)

    def test_timeout_during_external_call_does_not_accept_late_results(self):
        brand_id = self.make_brand(keywords=("one",))
        run_id, _ = prepare(self.engine, brand_id, queued=True)
        entered, release = Event(), Event()
        class SlowProvider(FakeProvider):
            def search(self, keyword):
                entered.set()
                if not release.wait(timeout=10):
                    raise RuntimeError("test timeout")
                return super().search(keyword)
        provider = SlowProvider()
        with ThreadPoolExecutor(max_workers=1) as executor:
            task = executor.submit(run_queued, self.engine, run_id, provider)
            self.assertTrue(entered.wait(timeout=10))
            with Session(self.engine) as db, db.begin():
                db.get(TrackingRun, run_id).lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            self.assertEqual(mark_stale(self.engine, 30), 1)
            release.set()
            with self.assertRaises(RunNotActive):
                task.result(timeout=10)
        self.assertEqual(provider.calls, [("search", "one")])
        with Session(self.engine) as db:
            self.assertEqual(db.get(TrackingRun, run_id).error_code, "worker_timeout")
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 0)

    def test_interrupted_run_can_be_recovered_with_a_new_run(self):
        brand_id = self.make_brand(keywords=("one", "two"))
        interrupted_id, _ = prepare(self.engine, brand_id, queued=True)

        class Interrupted(BaseException):
            pass

        class InterruptedProvider(FakeProvider):
            def search(self, keyword):
                if keyword == "two":
                    raise Interrupted()
                return super().search(keyword)

        # Giả lập tiến trình dừng đột ngột sau khi giao dịch bài đầu đã commit.
        with self.assertRaises(Interrupted):
            run_queued(self.engine, interrupted_id, InterruptedProvider())
        with Session(self.engine) as db, db.begin():
            run = db.get(TrackingRun, interrupted_id)
            self.assertEqual(run.status, "running")
            run.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Comment).where(Comment.brand_id == brand_id)), 1)
        with self.assertRaises(ValueError):
            prepare(self.engine, brand_id, queued=True)
        self.assertEqual(mark_stale(self.engine, 30), 1)
        replacement_id, _ = prepare(self.engine, brand_id, queued=True)
        self.assertEqual(run_queued(self.engine, replacement_id, FakeProvider(likes=9)), (replacement_id, "success"))
        with Session(self.engine) as db:
            self.assertEqual((db.get(TrackingRun, interrupted_id).status,
                              db.get(TrackingRun, interrupted_id).error_code), ("failed", "worker_timeout"))
            self.assertEqual(db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Comment).where(Comment.brand_id == brand_id)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(RunPostMatch).where(RunPostMatch.brand_id == brand_id)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(RunCommentMatch).where(RunCommentMatch.brand_id == brand_id)), 2)

    def test_firecrawl_http_envelope_to_database_with_mocked_network(self):
        brand_id = self.make_brand(keywords=("one",))
        calls = []
        def fake_open(request, timeout):
            capability = json.loads(request.data)["alexandria"]["capability"]
            calls.append(capability)
            if capability == "tiktok/search-videos":
                data = {"success": True, "search_item_list": [{"aweme_id": "v1", "url": "https://tiktok.com/@demo/video/1",
                        "create_time": int(time.time()),
                        "desc": "sample", "statistics": {"digg_count": 9}}]}
            else:
                data = {"success": True, "comments": [{"cid": "c1", "text": "sample", "digg_count": 1}]}
            return io.BytesIO(json.dumps({"success": True, "data": {"alexandria": [{"data": data}]}}).encode())
        opener = Mock(); opener.open.side_effect = fake_open
        with patch("app.firecrawl.build_opener", return_value=opener):
            run_id, status = run_once(self.engine, brand_id, FirecrawlTikTok("dummy", max_calls=2))
        self.assertEqual(status, "success")
        self.assertEqual(calls, ["tiktok/search-videos", "tiktok/video-comments"])
        search_options = json.loads(opener.open.call_args_list[0].args[0].data)["alexandria"]["options"]
        self.assertEqual((search_options["sort_by"], search_options["date_posted"]), ("relevance", "last-3-months"))
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(RunCommentMatch).where(RunCommentMatch.run_id == run_id)), 1)

    def test_lookback_window_drops_old_posts_and_records_notice(self):
        class WindowProvider(FakeProvider):
            def __init__(self, items):
                super().__init__()
                self.items = items

            def search(self, keyword):
                self.calls.append(("search", keyword))
                return self.items

        fresh = int(time.time()) - 86400
        old = int(time.time()) - 40 * 86400
        item = lambda vid, created: {"aweme_id": vid, "url": f"https://www.tiktok.com/@demo/video/{vid}", "desc": vid,
                                     "create_time": created, "statistics": {"digg_count": 1}}
        brand_id = self.make_brand(keywords=("one",))
        with Session(self.engine) as db, db.begin():
            db.get(TrackingConfig, brand_id).lookback_days = 30
        # Thứ tự TikTok được giữ; bài cũ hơn 30 ngày và bài không rõ ngày bị bỏ.
        provider = WindowProvider([item("new", fresh), item("old", old),
                                   {"aweme_id": "nodate", "url": "https://www.tiktok.com/@demo/video/x", "statistics": {}}])
        run_id, status = run_once(self.engine, brand_id, provider)
        self.assertEqual(status, "success")
        self.assertEqual([call for call in provider.calls if call[0] == "comments"],
                         [("comments", "https://www.tiktok.com/@demo/video/new")])
        with Session(self.engine) as db:
            attempt = db.scalar(select(TrackingAttempt).where(TrackingAttempt.run_id == run_id))
            self.assertEqual((attempt.status, attempt.result_count, attempt.notice), ("success", 1, "fewer_posts_in_window"))
            self.assertEqual(db.get(TrackingRun, run_id).config_snapshot["lookbackDays"], 30)
            self.assertEqual(set(db.scalars(select(Post.source_id).where(Post.brand_id == brand_id))), {"new"})

        run_id, status = run_once(self.engine, brand_id, WindowProvider([item("old", old)]))
        self.assertEqual(status, "success")
        with Session(self.engine) as db:
            attempt = db.scalar(select(TrackingAttempt).where(TrackingAttempt.run_id == run_id))
            self.assertEqual((attempt.status, attempt.result_count, attempt.notice), ("empty", 0, "no_posts_in_window"))

        # Đủ số bài trong khung thì không có thông báo, giữ đúng thứ tự trả về.
        with Session(self.engine) as db, db.begin():
            db.get(TrackingConfig, brand_id).post_limit = 2
        provider = WindowProvider([item("b", fresh), item("a", fresh), item("c", fresh)])
        run_id, _ = run_once(self.engine, brand_id, provider)
        self.assertEqual([call[1] for call in provider.calls if call[0] == "comments"],
                         ["https://www.tiktok.com/@demo/video/b", "https://www.tiktok.com/@demo/video/a"])
        with Session(self.engine) as db:
            self.assertIsNone(db.scalar(select(TrackingAttempt.notice).where(TrackingAttempt.run_id == run_id)))


if __name__ == "__main__":
    unittest.main()

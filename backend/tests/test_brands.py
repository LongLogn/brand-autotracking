"""Kiểm thử xác thực và cách ly; TEST_DATABASE_URL chỉ được trỏ đến DB thử nghiệm."""
import os
import time
import unittest
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, literal
from sqlalchemy.orm import Session

from app import auth
from app.database import session
from app.main import app, filter_posted_time
from app.models import Comment, EngagementSnapshot, Post, RunCommentMatch, RunPostMatch, TrackingAttempt, TrackingRun
from app.worker import work_once
from app.sentiment import classify_content

ISSUER = "https://cognito-idp.example.test/pool"
CLIENT_ID = "test-client"
PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class KeySource:
    def get_signing_key_from_jwt(self, token):
        return type("SigningKey", (), {"key": PRIVATE.public_key()})()


def token(subject, **extra):
    claims = {"iss": ISSUER, "sub": subject, "client_id": CLIENT_ID,
              "token_use": "access", "scope": "openid brand-api/access", "exp": int(time.time()) + 300}
    claims.update(extra)
    return jwt.encode(claims, PRIVATE, algorithm="RS256", headers={"kid": "test"})


class TimeFilterTests(unittest.TestCase):
    def test_bounds_and_invalid_times(self):
        from fastapi import HTTPException
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        engine = create_engine("sqlite://")
        with engine.connect() as db:
            query = select(literal(1))
            self.assertEqual(db.execute(filter_posted_time(query, literal(now), now, now + timedelta(seconds=1))).scalar(), 1)
            self.assertIsNone(db.execute(filter_posted_time(query, literal(now), None, now)).scalar())
            self.assertIsNone(db.execute(filter_posted_time(query, literal(None), now, None)).scalar())
        for start, end in ((datetime(2026, 1, 1), None), (now, now)):
            with self.assertRaises(HTTPException) as error:
                filter_posted_time(select(literal(1)), literal(now), start, end)
            self.assertEqual(error.exception.status_code, 422)
        engine.dispose()


class AlertRecipientsTests(unittest.TestCase):
    def test_validation(self):
        from app.main import AlertRecipients
        from pydantic import ValidationError
        self.assertEqual(AlertRecipients(emails=[" One@Example.com ", "two@example.com"]).emails,
                         ["one@example.com", "two@example.com"])
        for emails in (["invalid"], ["a@example.com", "A@example.com"], [f"{i}@example.com" for i in range(11)]):
            with self.assertRaises(ValidationError):
                AlertRecipients(emails=emails)

    def test_owned_recipients_and_empty_list(self):
        from sqlalchemy.pool import StaticPool
        from app.models import Base, Brand, User
        from app.auth import current_subject
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db, db.begin():
            owner = User(cognito_sub="owner"); other = User(cognito_sub="other")
            db.add_all([owner, other]); db.flush()
            brand = Brand(owner_id=owner.id, name="Test"); db.add(brand); db.flush()
            brand_id = brand.id
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        app.dependency_overrides[current_subject] = lambda: "owner"
        try:
            with TestClient(app) as client:
                path = f"/brands/{brand_id}/alert-recipients"
                self.assertEqual(client.get(path).json(), {"emails": []})
                self.assertEqual(client.put(path, json={"emails": ["A@example.com", "b@example.com"]}).json(),
                                 {"emails": ["a@example.com", "b@example.com"]})
                app.dependency_overrides[current_subject] = lambda: "other"
                self.assertEqual(client.get(path).status_code, 404)
                self.assertEqual(client.put(path, json={"emails": []}).status_code, 404)
                app.dependency_overrides[current_subject] = lambda: "owner"
                self.assertEqual(client.put(path, json={"emails": []}).json(), {"emails": []})
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


class CancelRunTests(unittest.TestCase):
    def test_cancel_ownership_idempotence_and_running_conflict(self):
        from sqlalchemy.pool import StaticPool
        from app.models import Base, Brand, User, TrackingRun, TrackingOutbox
        from app.auth import current_subject
        from app.lambda_worker import handle_queue
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db, db.begin():
            owner = User(cognito_sub="cancel-owner"); other = User(cognito_sub="cancel-other")
            db.add_all([owner, other]); db.flush()
            brand = Brand(owner_id=owner.id, name="Test"); db.add(brand); db.flush()
            run = TrackingRun(brand_id=brand.id, status="queued", config_snapshot={})
            running = TrackingRun(brand_id=brand.id, status="running", config_snapshot={})
            db.add_all([run, running]); db.flush()
            outbox = TrackingOutbox(run_id=run.id); db.add(outbox); db.flush()
            brand_id, run_id, running_id, event_id = brand.id, run.id, running.id, outbox.id
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        app.dependency_overrides[current_subject] = lambda: "cancel-other"
        try:
            with TestClient(app) as client:
                path = f"/brands/{brand_id}/runs/{run_id}/cancel"
                self.assertEqual(client.post(path).status_code, 404)
                app.dependency_overrides[current_subject] = lambda: "cancel-owner"
                response = client.post(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "cancelled")
                self.assertIsNotNone(response.json()["finished_at"])
                self.assertEqual(client.post(path).status_code, 200)
                self.assertEqual(client.post(f"/brands/{brand_id}/runs/{running_id}/cancel").status_code, 409)
                self.assertEqual(client.get(f"/brands/{brand_id}/runs").json()[0]["status"] in {"running", "cancelled"}, True)
            # An unpublished outbox entry for the cancelled run must not be sent.
            from app.outbox import publish_pending
            class Queue:
                def send_message(self, **kwargs):
                    raise AssertionError("cancelled run was published")
            self.assertEqual(publish_pending(engine, Queue(), "queue"), (0, 0))
            # A previously published message must not construct a provider or perform collection.
            import json
            with patch("app.lambda_worker.provider_for_run", side_effect=AssertionError("cancelled run was processed")):
                result = handle_queue(engine, [{"messageId": "m", "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}])
            self.assertEqual(result, {"batchItemFailures": []})
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class CancelRunRaceTests(unittest.TestCase):
    def test_cancel_and_worker_claim_are_serialized(self):
        from app.main import cancel_run
        from app.models import Base, Brand, User, TrackingConfig, TrackingRun
        from app.tracking import RunNotQueued, run_queued
        from fastapi import HTTPException
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        Base.metadata.create_all(engine)
        try:
            for _ in range(5):
                with Session(engine) as db, db.begin():
                    user = User(cognito_sub=str(uuid4())); db.add(user); db.flush()
                    brand = Brand(owner_id=user.id, name="race"); db.add(brand); db.flush()
                    db.add(TrackingConfig(brand_id=brand.id, frequency="daily", run_time="08:00", timezone="UTC", post_limit=1, active=True))
                    run = TrackingRun(brand_id=brand.id, status="queued", config_snapshot={}); db.add(run); db.flush()
                    brand_id, run_id, subject = brand.id, run.id, user.cognito_sub
                gate = Barrier(2)
                def cancel():
                    gate.wait()
                    with Session(engine) as db:
                        try:
                            return cancel_run(brand_id, run_id, subject, db).status
                        except HTTPException as exc:
                            return exc.status_code
                def claim():
                    gate.wait()
                    try:
                        run_queued(engine, run_id, object())
                        return "claimed"
                    except RunNotQueued:
                        return "not_queued"
                with patch("app.tracking.process", return_value=(run_id, "success")):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        a = pool.submit(cancel); b = pool.submit(claim)
                        outcomes = a.result(), b.result()
                self.assertIn(outcomes, [("cancelled", "not_queued"), (409, "claimed")])
        finally:
            engine.dispose()


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.config = patch.object(auth, "configuration", return_value=(ISSUER, CLIENT_ID, KeySource()))
        self.config.start()

    def tearDown(self):
        self.config.stop()
        app.dependency_overrides.clear()
        self.client.close()

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
    def test_delete_brand_checks_owner_and_active_work_and_removes_data(self):
        from uuid import UUID
        from app.models import (Alert, AnalysisJob, AttemptPostMatch, Brand, BrandKeyword, TrackingConfig,
                                TrackingOutbox, SentimentResult, SentimentWork)
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        owner = {"Authorization": f"Bearer {token(str(uuid4()))}"}
        other = {"Authorization": f"Bearer {token(str(uuid4()))}"}
        brand_id = self.client.post('/brands', json={'name': 'Delete test'}, headers=owner).json()['id']
        config = {'keywords': ['coffee'], 'platforms': ['tiktok'], 'frequency': 'daily',
                  'runTime': '08:00', 'timezone': 'UTC', 'postLimit': 1, 'active': True}
        self.assertEqual(self.client.put(f'/brands/{brand_id}/tracking', json=config, headers=owner).status_code, 200)
        rule = {'enabled': True, 'growth_percent': 50, 'window_days': 1, 'minimum_current': 1, 'absolute_threshold': None}
        self.assertEqual(self.client.put(f'/brands/{brand_id}/alert-rules/post', json=rule, headers=owner).status_code, 200)
        self.assertEqual(self.client.delete(f'/brands/{brand_id}', headers=other).status_code, 404)
        run_id = self.client.post(f'/brands/{brand_id}/runs', headers=owner).json()['id']
        self.assertEqual(self.client.delete(f'/brands/{brand_id}', headers=owner).status_code, 409)
        now = datetime.now(timezone.utc)
        with Session(engine) as db, db.begin():
            run = db.get(TrackingRun, UUID(run_id)); run.status = 'success'; run.finished_at = now
            post = Post(brand_id=UUID(brand_id), source='tiktok', source_id='fixture',
                        url='https://example.test/post', content='Bài thử', first_seen_at=now)
            db.add(post); db.flush()
            comment = Comment(brand_id=UUID(brand_id), post_id=post.id, source_id='comment', content='Bình luận thử')
            db.add(comment); db.flush()
            db.add(RunPostMatch(run_id=run.id, post_id=post.id, brand_id=run.brand_id))
            attempt = TrackingAttempt(run_id=run.id, source='tiktok', keyword='coffee', status='success', result_count=1)
            db.add(attempt)
            db.flush()
            db.add(RunCommentMatch(run_id=run.id, post_id=post.id, comment_id=comment.id, brand_id=run.brand_id))
            db.add(AttemptPostMatch(attempt_id=attempt.id, run_id=run.id, post_id=post.id, brand_id=run.brand_id))
            db.add(EngagementSnapshot(run_id=run.id, brand_id=run.brand_id, post_id=post.id, captured_at=now, likes=2))
            db.add(SentimentResult(brand_id=run.brand_id, post_id=post.id, content_hash='0' * 64,
                                   label='negative', model_id='fixture', classified_at=now))
            db.add(Alert(brand_id=run.brand_id, content_type='post', window_start=now - timedelta(days=1), window_end=now,
                         previous_negative=1, current_negative=2, growth_percent=50, minimum_current=1, reason='growth'))
            db.add(SentimentWork(run_id=run.id, status='running', failures=0, next_attempt_at=now,
                                 lease_token=uuid4(), lease_expires_at=now + timedelta(minutes=1), updated_at=now))
        self.assertEqual(self.client.delete(f'/brands/{brand_id}', headers=owner).status_code, 409)
        with Session(engine) as db, db.begin():
            work = db.get(SentimentWork, UUID(run_id)); work.status = 'pending'; work.lease_token = None; work.lease_expires_at = None
            job = AnalysisJob(brand_id=UUID(brand_id), request_key=uuid4(), status='running',
                              window_start=now - timedelta(days=1), window_end=now, model_id='fixture')
            db.add(job); db.flush(); job_id = job.id
        self.assertEqual(self.client.delete(f'/brands/{brand_id}', headers=owner).status_code, 409)
        with Session(engine) as db, db.begin():
            db.get(AnalysisJob, job_id).status = 'failed'
        response = self.client.delete(f'/brands/{brand_id}', headers=owner)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'deleted': True})
        self.assertEqual(self.client.get(f'/brands/{brand_id}/tracking', headers=owner).status_code, 404)
        with Session(engine) as db:
            self.assertIsNone(db.get(Brand, UUID(brand_id)))
            self.assertIsNone(db.get(TrackingConfig, UUID(brand_id)))
            self.assertEqual(db.scalars(select(BrandKeyword).where(BrandKeyword.brand_id == UUID(brand_id))).all(), [])
            self.assertIsNone(db.get(TrackingRun, UUID(run_id)))
            self.assertEqual(db.scalars(select(TrackingOutbox).where(TrackingOutbox.run_id == UUID(run_id))).all(), [])
        engine.dispose()

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
    def test_delete_racing_with_enqueue_keeps_consistent_state(self):
        from uuid import UUID
        from app.models import Brand
        engine = create_engine(os.environ['TEST_DATABASE_URL'])
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        headers = {'Authorization': f'Bearer {token(str(uuid4()))}'}
        brand = self.client.post('/brands', json={'name': 'Delete race'}, headers=headers).json()['id']
        config = {'keywords': ['coffee'], 'platforms': ['tiktok'], 'frequency': 'daily',
                  'runTime': '08:00', 'timezone': 'UTC', 'postLimit': 1, 'active': True}
        self.assertEqual(self.client.put(f'/brands/{brand}/tracking', json=config, headers=headers).status_code, 200)
        barrier = Barrier(2)
        def remove():
            barrier.wait(); return self.client.delete(f'/brands/{brand}', headers=headers).status_code
        def enqueue():
            barrier.wait(); return self.client.post(f'/brands/{brand}/runs', headers=headers).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            deleted = executor.submit(remove); queued = executor.submit(enqueue)
            deleted, queued = deleted.result(), queued.result()
        self.assertIn((deleted, queued), {(200, 404), (200, 409), (409, 202)})
        with Session(engine) as db, db.begin():
            if deleted == 200:
                self.assertIsNone(db.get(Brand, UUID(brand)))
                self.assertEqual(db.scalars(select(TrackingRun).where(TrackingRun.brand_id == UUID(brand))).all(), [])
            else:
                run = db.scalar(select(TrackingRun).where(TrackingRun.brand_id == UUID(brand)))
                self.assertEqual(run.status, 'queued')
                run.status = 'failed'; run.finished_at = datetime.now(timezone.utc)
        if deleted != 200:
            self.assertEqual(self.client.delete(f'/brands/{brand}', headers=headers).status_code, 200)
        engine.dispose()

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
    def test_alert_rules_are_owned_validated_and_replaceable(self):
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        ha = {"Authorization": f"Bearer {token(str(uuid4()))}"}
        hb = {"Authorization": f"Bearer {token(str(uuid4()))}"}
        brand = self.client.post("/brands", json={"name": "Alerts"}, headers=ha).json()["id"]
        path = f"/brands/{brand}/alert-rules"
        rule = {"enabled": True, "growth_percent": 50, "window_days": 7,
                "minimum_current": 5, "absolute_threshold": None}
        self.assertEqual(self.client.get(path, headers=ha).json(), [])
        self.assertEqual(self.client.put(f"{path}/comment", json=rule, headers=ha).json(),
                         {**rule, "content_type": "comment"})
        self.assertEqual(self.client.get(path, headers=hb).status_code, 404)
        self.assertEqual(self.client.put(f"{path}/comment", json=rule, headers=hb).status_code, 404)
        for changed in ({"growth_percent": -1}, {"window_days": 0}, {"minimum_current": True},
                        {"absolute_threshold": 0}, {"enabled": 1}, {"owner_id": "other"}):
            self.assertEqual(self.client.put(f"{path}/comment", json={**rule, **changed}, headers=ha).status_code, 422)
        self.assertEqual(self.client.put(f"{path}/unknown", json=rule, headers=ha).status_code, 422)
        updated = {**rule, "enabled": False, "absolute_threshold": 15}
        self.assertEqual(self.client.put(f"{path}/comment", json=updated, headers=ha).status_code, 200)
        self.assertEqual(self.client.get(path, headers=ha).json(), [{**updated, "content_type": "comment"}])
        engine.dispose()

    def test_reject_missing_id_expired_wrong_client_and_forged_tokens(self):
        db_dependency = app.dependency_overrides
        db_dependency[session] = lambda: None
        for value in (None, token("u", token_use="id"), token("u", exp=1),
                      token("u", client_id="wrong"), token("u") + "x"):
            headers = {"Authorization": f"Bearer {value}"} if value else {}
            self.assertEqual(self.client.get("/brands", headers=headers).status_code, 401)

    def test_unavailable_auth_service_is_not_an_invalid_token(self):
        app.dependency_overrides[session] = lambda: None
        with patch.object(auth, "configuration", side_effect=RuntimeError("configuration")):
            response = self.client.get("/brands", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("configuration", response.text)

    def test_requires_exact_api_scope(self):
        app.dependency_overrides[session] = lambda: None
        for value in ("", "openid", "brand-api/access-extra", None):
            response = self.client.get("/brands", headers={"Authorization": f"Bearer {token('u', scope=value)}"})
            self.assertEqual(response.status_code, 403)

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
    def test_create_idempotency_is_scoped_and_rejects_changed_payload(self):
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        key, a, b = str(uuid4()), str(uuid4()), str(uuid4())
        ha = {"Authorization": f"Bearer {token(a)}", "Idempotency-Key": key}
        hb = {"Authorization": f"Bearer {token(b)}", "Idempotency-Key": key}
        first = self.client.post("/brands", json={"name": " Test "}, headers=ha)
        again = self.client.post("/brands", json={"name": "Test"}, headers=ha)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["id"], again.json()["id"])
        self.assertEqual(self.client.post("/brands", json={"name": "Other"}, headers=ha).status_code, 409)
        other = self.client.post("/brands", json={"name": "Other"}, headers=hb)
        self.assertEqual(other.status_code, 201)
        self.assertNotEqual(first.json()["id"], other.json()["id"])
        self.assertEqual(len(self.client.get("/brands", headers=ha).json()), 1)
        engine.dispose()

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
    def test_concurrent_create_with_same_key_creates_one_brand(self):
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        headers = {"Authorization": f"Bearer {token(str(uuid4()))}", "Idempotency-Key": str(uuid4())}
        def create():
            return self.client.post("/brands", json={"name": "Concurrent"}, headers=headers)
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: create(), range(2)))
        self.assertEqual([response.status_code for response in responses], [201, 201])
        self.assertEqual(responses[0].json()["id"], responses[1].json()["id"])
        self.assertEqual(len(self.client.get("/brands", headers=headers).json()), 1)
        engine.dispose()

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
    def test_owner_isolation_and_input_validation(self):
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        def test_session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[session] = test_session
        a, b = str(uuid4()), str(uuid4())
        ha, hb = {"Authorization": f"Bearer {token(a)}"}, {"Authorization": f"Bearer {token(b)}"}
        response = self.client.post("/brands", json={"name": "  Test brand  "}, headers=ha)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Test brand")
        brand_id = response.json()["id"]
        self.assertEqual(len(self.client.get("/brands", headers=ha).json()), 1)
        self.assertEqual(self.client.get("/brands", headers=hb).json(), [])
        brand_path = f"/brands/{brand_id}"
        self.assertEqual(self.client.put(brand_path, json={"name": "  Tên mới  "}, headers=ha).json()["name"], "Tên mới")
        self.assertEqual(self.client.put(brand_path, json={"name": "Khác"}, headers=hb).status_code, 404)
        self.assertEqual(self.client.put(brand_path, json={"name": " "}, headers=ha).status_code, 422)
        self.assertEqual(self.client.get("/brands", headers=ha).json()[0]["name"], "Tên mới")
        self.assertEqual(self.client.post("/brands", json={"name": " ", "owner_id": b}, headers=ha).status_code, 422)
        path = f"/brands/{brand_id}/tracking"
        settings = {"keywords": ["cà phê", "brand"], "platforms": ["tiktok"], "frequency": "daily",
                    "runTime": "08:00", "timezone": "Asia/Ho_Chi_Minh", "postLimit": 10, "active": True}
        self.assertEqual(self.client.put(path, json=settings, headers=ha).status_code, 200)
        for sources in (["reddit"], ["tiktok", "threads"]):
            invalid = self.client.put(path, json={**settings, "platforms": sources}, headers=ha)
            self.assertEqual(invalid.status_code, 422)
            self.assertIn(sources[-1], invalid.text)
            self.assertEqual(self.client.get(path, headers=ha).json()["platforms"], ["tiktok"])
        from app.models import BrandSource
        from uuid import UUID
        with Session(engine) as db, db.begin():
            db.add(BrandSource(brand_id=UUID(brand_id), source="facebook"))
        self.assertCountEqual(self.client.get(path, headers=ha).json()["platforms"], ["facebook", "tiktok"])
        self.assertEqual(self.client.put(path, json=settings, headers=ha).status_code, 200)
        saved = self.client.get(path, headers=ha).json()
        self.assertEqual(saved["platforms"], ["tiktok"])
        self.assertEqual(saved["keywords"], ["brand", "cà phê"])
        self.assertIsNotNone(saved["nextRunAt"])
        self.assertEqual(self.client.put(path, json=settings, headers=ha).status_code, 200)
        self.assertEqual(self.client.get(path, headers=ha).json()["nextRunAt"], saved["nextRunAt"])
        self.assertEqual(self.client.get(path, headers=hb).status_code, 404)
        self.assertEqual(self.client.put(path, json=settings, headers=hb).status_code, 404)
        self.assertEqual(self.client.put(path, json={**settings, "runTime": "25:00"}, headers=ha).status_code, 422)
        self.assertEqual(self.client.put(path, json={**settings, "keywords": ["Abc", "abc"]}, headers=ha).status_code, 422)
        self.assertEqual(self.client.get(path, headers=ha).json()["runTime"], "08:00")
        now = datetime.now(timezone.utc)
        from uuid import UUID
        with Session(engine) as db:
            run = TrackingRun(brand_id=UUID(brand_id), started_at=now, status="success", config_snapshot={})
            post = Post(brand_id=UUID(brand_id), source="tiktok", source_id="post-1", url="https://example.test/post", content="test post", first_seen_at=now, posted_at=now)
            db.add_all([run, post]); db.flush()
            comment = Comment(brand_id=UUID(brand_id), post_id=post.id, source_id="comment-1", content="test", posted_at=now)
            unknown = Comment(brand_id=UUID(brand_id), post_id=post.id, source_id=None, content="unknown")
            db.add_all([comment, unknown]); db.flush()
            later_run = TrackingRun(brand_id=UUID(brand_id), started_at=now + timedelta(minutes=1), status="partial", config_snapshot={})
            db.add(later_run); db.flush()
            low_post = Post(brand_id=UUID(brand_id), source="tiktok", source_id="post-low", url="https://example.test/low", first_seen_at=now + timedelta(minutes=3))
            db.add(low_post); db.flush()
            db.add_all([EngagementSnapshot(brand_id=UUID(brand_id), run_id=run.id, post_id=post.id,
                                           captured_at=now, likes=None, views=9),
                        EngagementSnapshot(brand_id=UUID(brand_id), run_id=later_run.id, post_id=post.id,
                                           captured_at=now + timedelta(minutes=1), likes=5, views=12),
                        EngagementSnapshot(brand_id=UUID(brand_id), run_id=run.id, comment_id=comment.id,
                                           captured_at=now, likes=2),
                        EngagementSnapshot(brand_id=UUID(brand_id), run_id=later_run.id, post_id=low_post.id,
                                           captured_at=now + timedelta(minutes=2), likes=1),
                        RunPostMatch(run_id=run.id, post_id=post.id, brand_id=UUID(brand_id)),
                        TrackingAttempt(run_id=run.id, source="tiktok", keyword="brand", status="empty", result_count=0)])
            db.flush()
            db.add(RunCommentMatch(run_id=run.id, comment_id=comment.id, post_id=post.id, brand_id=UUID(brand_id)))
            post_id = str(post.id)
            comment_id = str(comment.id)
            run_id = str(run.id)
            db.commit()
        self.assertEqual(len(self.client.get(f"/brands/{brand_id}/runs", headers=ha).json()), 2)
        overview = self.client.get(f"/brands/{brand_id}/overview", headers=ha)
        self.assertEqual(overview.status_code, 200)
        self.assertEqual((overview.json()["post_count"], overview.json()["comment_count"],
                          overview.json()["run_count"]), (2, 2, 2))
        self.assertIn(overview.json()["latest_run"]["status"], ("success", "partial"))
        self.assertEqual(self.client.get(f"/brands/{brand_id}/overview", headers=hb).status_code, 404)
        posts = self.client.get(f"/brands/{brand_id}/mentions", headers=ha).json()
        self.assertEqual(posts[0]["sentiment"], "unknown")
        classify_content(engine, UUID(brand_id), "post", UUID(post_id), lambda _: "negative", "fake")
        classify_content(engine, UUID(brand_id), "comment", UUID(comment_id), lambda _: "positive", "fake")
        self.assertEqual(self.client.get(f"/brands/{brand_id}/mentions", headers=ha).json()[0]["sentiment"], "negative")
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs/{run_id}/mentions/{post_id}/comments", headers=ha).json()[0]["sentiment"], "positive")
        with Session(engine) as db, db.begin():
            db.get(Comment, UUID(comment_id)).content = "changed"
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs/{run_id}/mentions/{post_id}/comments", headers=ha).json()[0]["sentiment"], "unknown")
        self.assertEqual(posts[0]["metrics"]["views"], 12)
        self.assertEqual([row["metrics"]["likes"] for row in posts], [5, 1])
        self.assertFalse(posts[0]["maybe_duplicate"])
        filtered = self.client.get(f"/brands/{brand_id}/mentions", headers=ha,
                                   params={"source": "tiktok", "posted_from": (now - timedelta(seconds=1)).isoformat(),
                                           "posted_until": (now + timedelta(seconds=1)).isoformat()})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([row["id"] for row in filtered.json()], [post_id])
        self.assertEqual(self.client.get(f"/brands/{brand_id}/mentions", headers=ha,
                                         params={"source": "reddit"}).json(), [])
        self.assertEqual(self.client.get(f"/brands/{brand_id}/mentions", headers=ha,
                                         params={"posted_from": "2026-01-01T00:00:00"}).status_code, 422)
        self.assertEqual(self.client.get(f"/brands/{brand_id}/mentions", headers=ha,
                                         params={"posted_from": now.isoformat(), "posted_until": now.isoformat()}).status_code, 422)
        run_posts = self.client.get(f"/brands/{brand_id}/runs/{run_id}/mentions", headers=ha).json()
        self.assertEqual(run_posts[0]["metrics"]["views"], 9)
        self.assertIsNone(run_posts[0]["metrics"]["likes"])
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs/{run_id}", headers=ha).json()["attempts"][0]["status"], "empty")
        comments = self.client.get(f"/brands/{brand_id}/mentions/{post_id}/comments", headers=ha).json()
        self.assertEqual(comments[0]["source_id"], "comment-1")
        self.assertTrue(comments[-1]["maybe_duplicate"])
        self.assertTrue(any(row["maybe_duplicate"] and row["metrics"] is None for row in comments))
        self.assertEqual(next(row for row in comments if row["source_id"] == "comment-1")["metrics"]["likes"], 2)
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs/{run_id}/mentions/{post_id}/comments", headers=ha).json()[0]["metrics"]["likes"], 2)
        for comment_path in (f"/brands/{brand_id}/mentions/{post_id}/comments",
                             f"/brands/{brand_id}/runs/{run_id}/mentions/{post_id}/comments"):
            result = self.client.get(comment_path, headers=ha, params={"posted_from": now.isoformat(),
                                     "posted_until": (now + timedelta(seconds=1)).isoformat()})
            self.assertEqual([row["source_id"] for row in result.json()], ["comment-1"])
            self.assertEqual(self.client.get(comment_path, headers=ha, params={"posted_until": now.isoformat()}).json(), [])
            self.assertEqual(self.client.get(comment_path, headers=ha, params={"posted_from": "2026-01-01T00:00:00"}).status_code, 422)
            self.assertEqual(self.client.get(comment_path, headers=ha, params={"posted_from": now.isoformat(), "posted_until": now.isoformat()}).status_code, 422)
            self.assertEqual(self.client.get(comment_path, headers=hb, params={"posted_from": now.isoformat()}).status_code, 404)
        self.assertEqual(self.client.get(f"/brands/{brand_id}/mentions", headers=hb).status_code, 404)
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs/{run_id}", headers=hb).status_code, 404)
        self.assertEqual(self.client.get(f"/brands/{brand_id}/mentions/{post_id}/comments", headers=hb).status_code, 404)
        before = self.client.get(f"/brands/{brand_id}/runs", headers=ha).json()
        with patch("app.main.manual_worker_status", return_value="stopped"):
            stopped = self.client.post(f"/brands/{brand_id}/runs", headers=ha)
        self.assertEqual((stopped.status_code, stopped.json()["detail"]), (503, "tracking_worker_stopped"))
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs", headers=ha).json(), before)
        with patch("app.main.manual_worker_status", return_value="ready"):
            queued = self.client.post(f"/brands/{brand_id}/runs", headers=ha)
        self.assertEqual(queued.status_code, 202)
        self.assertEqual(queued.json()["worker_status"], "ready")
        self.assertEqual(queued.json()["status"], "queued")
        self.assertEqual(self.client.post(f"/brands/{brand_id}/runs", headers=ha).status_code, 409)
        self.assertEqual(self.client.post(f"/brands/{brand_id}/runs", headers=hb).status_code, 404)
        class FakeProvider:
            def search(self, keyword):
                return [{"aweme_id": "video-2", "url": "https://tiktok.com/@test/video/2", "desc": "sample",
                         "statistics": {"digg_count": 8, "comment_count": 1}}]
            def comments(self, url):
                return [{"cid": "comment-2", "text": "sample comment", "digg_count": 3}]
        queued_id = UUID(queued.json()["id"])
        self.assertEqual(work_once(engine, FakeProvider), (queued_id, "success"))
        run_detail = self.client.get(f"/brands/{brand_id}/runs/{queued_id}", headers=ha).json()
        self.assertEqual(run_detail["status"], "success")
        self.assertEqual(run_detail["collection_limits"], {"search_pages": 1, "comment_pages": 1})
        self.assertEqual(len(run_detail["attempts"]), 2)
        attempt_id = run_detail["attempts"][0]["id"]
        self.assertEqual(len(self.client.get(f"/brands/{brand_id}/runs/{queued_id}/attempts/{attempt_id}/mentions", headers=ha).json()), 1)
        self.assertEqual(self.client.get(f"/brands/{brand_id}/runs/{queued_id}/attempts/{attempt_id}/mentions", headers=hb).status_code, 404)
        mentions = self.client.get(f"/brands/{brand_id}/runs/{queued_id}/mentions", headers=ha).json()
        self.assertEqual(mentions[0]["metrics"]["likes"], 8)
        comments = self.client.get(f"/brands/{brand_id}/runs/{queued_id}/mentions/{mentions[0]['id']}/comments", headers=ha).json()
        self.assertEqual(comments[0]["metrics"]["likes"], 3)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()

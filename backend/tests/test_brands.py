"""Kiểm thử xác thực và cách ly; TEST_DATABASE_URL chỉ được trỏ đến DB thử nghiệm."""
import os
import time
import unittest
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


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.config = patch.object(auth, "configuration", return_value=(ISSUER, CLIENT_ID, KeySource()))
        self.config.start()

    def tearDown(self):
        self.config.stop()
        app.dependency_overrides.clear()
        self.client.close()

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
        saved = self.client.get(path, headers=ha).json()
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
            post = Post(brand_id=UUID(brand_id), source="tiktok", source_id="post-1", url="https://example.test/post", first_seen_at=now, posted_at=now)
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
        queued = self.client.post(f"/brands/{brand_id}/runs", headers=ha)
        self.assertEqual(queued.status_code, 202)
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

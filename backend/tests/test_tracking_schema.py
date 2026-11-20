"""Ràng buộc liên kết và giá trị thiếu trên PostgreSQL thử nghiệm."""
import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AttemptPostMatch, Brand, Comment, EngagementSnapshot, Post, RunCommentMatch, RunPostMatch, TrackingAttempt, TrackingRun, User


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Cần PostgreSQL thử nghiệm")
class TrackingSchemaTests(unittest.TestCase):
    def test_source_ids_nullable_and_matches_cannot_cross_brand(self):
        engine = create_engine(os.environ["TEST_DATABASE_URL"])
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            user = User(cognito_sub=str(uuid4()))
            db.add(user)
            db.flush()
            a, b = Brand(owner_id=user.id, name="A"), Brand(owner_id=user.id, name="B")
            db.add_all([a, b]); db.flush()
            run = TrackingRun(brand_id=a.id, started_at=now, status="running", config_snapshot={})
            pa = Post(brand_id=a.id, source="tiktok", source_id="video-a", url="https://example.test/a", first_seen_at=now)
            pb = Post(brand_id=b.id, source="tiktok", source_id="video-b", url="https://example.test/b", first_seen_at=now)
            db.add_all([run, pa, pb]); db.flush()
            ca = Comment(brand_id=a.id, post_id=pa.id, source_id="comment-a", content="sample")
            attempt = TrackingAttempt(run_id=run.id, source="tiktok", keyword="a", status="success")
            db.add_all([ca, attempt]); db.flush()
            db.add(RunPostMatch(run_id=run.id, post_id=pa.id, brand_id=a.id)); db.flush()
            db.add_all([RunCommentMatch(run_id=run.id, comment_id=ca.id, post_id=pa.id, brand_id=a.id),
                        EngagementSnapshot(run_id=run.id, brand_id=a.id, post_id=pa.id, captured_at=now, likes=None)])
            db.flush()
            other_run = TrackingRun(brand_id=a.id, started_at=now, status="running", config_snapshot={})
            db.add(other_run); db.flush()
            with self.assertRaises(IntegrityError), db.begin_nested():
                db.add(RunCommentMatch(run_id=other_run.id, comment_id=ca.id, post_id=pa.id, brand_id=a.id)); db.flush()
            with self.assertRaises(IntegrityError), db.begin_nested():
                db.add(RunPostMatch(run_id=run.id, post_id=pb.id, brand_id=a.id)); db.flush()
            with self.assertRaises(IntegrityError), db.begin_nested():
                db.add(AttemptPostMatch(attempt_id=attempt.id, run_id=run.id, post_id=pb.id, brand_id=a.id)); db.flush()
            with self.assertRaises(IntegrityError), db.begin_nested():
                db.add(Comment(brand_id=a.id, post_id=pb.id, content="cross-brand")); db.flush()
            with self.assertRaises(IntegrityError), db.begin_nested():
                db.add(EngagementSnapshot(run_id=run.id, brand_id=a.id, captured_at=now)); db.flush()
            with self.assertRaises(IntegrityError), db.begin_nested():
                db.add(Post(brand_id=a.id, source="tiktok", source_id="video-a", url="https://example.test/dup", first_seen_at=now)); db.flush()
            # Thiếu source_id không bị gộp tự động: cần cảnh báo khả năng trùng ở tầng ứng dụng.
            db.add_all([Comment(brand_id=a.id, post_id=pa.id, source_id=None, content="unknown"),
                        Comment(brand_id=a.id, post_id=pa.id, source_id=None, content="unknown")])
            db.flush()
            db.rollback()
        engine.dispose()


if __name__ == "__main__":
    unittest.main()

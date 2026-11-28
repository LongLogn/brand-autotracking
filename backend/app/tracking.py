"""Tạo, nhận và xử lý phiên tracking với lease và fencing."""
import os
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.adapters.tiktok import comment_record, ranked_posts, relevant_posts
from app.firecrawl import FirecrawlTikTok, ProviderError
from app.sentiment import content_hash
from app.models import (AttemptPostMatch, Brand, BrandKeyword, BrandSource, Comment, EngagementSnapshot, Post, SentimentWork,
                        RunCommentMatch, RunPostMatch, TrackingAttempt, TrackingConfig, TrackingOutbox, TrackingRun)


class RunNotQueued(ValueError):
    pass


class RunNotActive(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc)


def database_now(db):
    return db.scalar(select(func.clock_timestamp()))


def parsed(value):
    return datetime.fromisoformat(value) if value else None


def lease_duration():
    seconds = int(os.environ.get("WORKER_LEASE_SECONDS", "600"))
    if not 30 <= seconds <= 3600:
        raise ValueError("Thời hạn lease phải từ 30 đến 3600 giây")
    return timedelta(seconds=seconds)
HEARTBEAT_INTERVAL_SECONDS = 60


class LeaseHeartbeat:
    """Gia hạn lease trong lúc lời gọi provider đang chờ phản hồi."""

    def __init__(self, engine, run_id, brand_id, lease_token, interval_seconds=None):
        if interval_seconds is None:
            interval_seconds = min(HEARTBEAT_INTERVAL_SECONDS, max(5, lease_duration().total_seconds() / 3))
        if interval_seconds <= 0:
            raise ValueError("Khoảng heartbeat phải dương")
        self.engine, self.run_id, self.brand_id, self.lease_token = engine, run_id, brand_id, lease_token
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._error = None
        self._thread = Thread(target=self._run, name=f"tracking-heartbeat-{run_id}", daemon=True)

    def _run(self):
        while not self._stop.wait(self.interval_seconds):
            try:
                ensure_active(self.engine, self.run_id, self.brand_id, self.lease_token)
            except Exception as exc:
                self._error = exc
                return

    def start(self):
        self._thread.start()
        return self

    def check(self):
        if self._error is not None:
            raise RunNotActive("Không thể gia hạn lease") from self._error

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=min(self.interval_seconds, 5))


def active_run(db, run_id, lease_token, brand_id=None):
    run = db.scalar(select(TrackingRun).where(TrackingRun.id == run_id).with_for_update())
    if (run is None or run.status != "running" or lease_token is None or run.lease_token != lease_token
            or run.lease_expires_at is None or run.lease_expires_at <= database_now(db)
            or (brand_id is not None and run.brand_id != brand_id)):
        raise RunNotActive("Phiên không còn hoạt động")
    return run


def ensure_active(engine, run_id, brand_id, lease_token):
    with Session(engine) as db, db.begin():
        run = active_run(db, run_id, lease_token, brand_id)
        run.lease_expires_at = database_now(db) + lease_duration()


def prepare(engine, brand_id, queued=False):
    """Khóa nhãn hàng khi tạo phiên để ngăn hai phiên thủ công đồng thời."""
    with Session(engine) as db, db.begin():
        brand = db.scalar(select(Brand).where(Brand.id == brand_id).with_for_update())
        config = db.get(TrackingConfig, brand_id)
        if brand is None or config is None:
            raise ValueError("Không có nhãn hàng hoặc cấu hình")
        if not config.active:
            raise ValueError("Cấu hình tracking đang tạm dừng")
        running = db.scalar(select(TrackingRun.id).where(TrackingRun.brand_id == brand_id, TrackingRun.status.in_(["queued", "running"])))
        if running:
            raise ValueError("Đã có phiên đang chạy")
        keywords = db.scalars(select(BrandKeyword.keyword).where(BrandKeyword.brand_id == brand_id).order_by(BrandKeyword.keyword)).all()
        sources = db.scalars(select(BrandSource.source).where(BrandSource.brand_id == brand_id).order_by(BrandSource.source)).all()
        if not keywords or not sources or not 1 <= config.post_limit <= 50:
            raise ValueError("Cấu hình tracking không hợp lệ")
        snapshot = {"brand_name": brand.name, "keywords": list(keywords), "sources": list(sources), "postLimit": config.post_limit,
                    "frequency": config.frequency, "runTime": config.run_time, "timezone": config.timezone,
                    "search_pages": 1, "comment_pages": 1}
        created_at = database_now(db)
        run = TrackingRun(brand_id=brand_id, status="queued" if queued else "running", queued_at=created_at,
                          started_at=None if queued else created_at, config_snapshot=snapshot,
                          lease_token=None if queued else uuid4(),
                          lease_expires_at=None if queued else created_at + lease_duration())
        db.add(run)
        db.flush()
        if queued:
            db.add(TrackingOutbox(run_id=run.id))
        return run.id, snapshot


def save_post(engine, run_id, brand_id, data, raw_comments, lease_token):
    """Lưu một bài và bình luận trong một giao dịch; chỉ số null là không khả dụng."""
    with Session(engine) as db, db.begin():
        active_run(db, run_id, lease_token, brand_id)
        observed_at = database_now(db)
        source_id = data["source_id"]
        post = None
        if source_id:
            post = db.scalar(select(Post).where(Post.brand_id == brand_id, Post.source == data["source"], Post.source_id == source_id))
        if post is None:
            post = Post(brand_id=brand_id, source=data["source"], source_id=source_id, url=data["url"],
                        content=data["content"], posted_at=parsed(data["posted_at"]), first_seen_at=now())
            db.add(post)
            db.flush()
        else:
            post.url = data["url"]
            if data["content"] is not None:
                post.content = data["content"]
            if data["posted_at"] is not None:
                post.posted_at = parsed(data["posted_at"])
        match = db.get(RunPostMatch, (run_id, post.id))
        if match is not None:
            # Không tạo lại bình luận thiếu ID khi cùng bài xuất hiện qua từ khóa khác.
            return post.id
        db.add(RunPostMatch(run_id=run_id, post_id=post.id, brand_id=brand_id,
                            observed_at=observed_at,
                            content_hash=content_hash(data["content"]) if data["content"] is not None else None))
        db.flush()
        db.add(EngagementSnapshot(run_id=run_id, brand_id=brand_id, post_id=post.id,
                                  captured_at=now(), likes=data["likes"], views=data["views"],
                                  shares=data["shares"], comment_count=data["comment_count"]))
        for item in raw_comments:
            row = comment_record(item)
            if row is None:
                continue
            comment = None
            if row["source_id"]:
                comment = db.scalar(select(Comment).where(Comment.post_id == post.id, Comment.source_id == row["source_id"]))
            if comment is None:
                comment = Comment(brand_id=brand_id, post_id=post.id, source_id=row["source_id"],
                                  content=row["content"], posted_at=parsed(row["posted_at"]))
                db.add(comment)
                db.flush()
            else:
                comment.content = row["content"]
                if row["posted_at"] is not None:
                    comment.posted_at = parsed(row["posted_at"])
            if db.get(RunCommentMatch, (run_id, comment.id)) is None:
                db.add(RunCommentMatch(run_id=run_id, comment_id=comment.id, post_id=post.id, brand_id=brand_id,
                                       observed_at=observed_at, content_hash=content_hash(row["content"])))
                db.add(EngagementSnapshot(run_id=run_id, brand_id=brand_id, comment_id=comment.id,
                                          captured_at=now(), likes=row["likes"]))
                db.flush()
        return post.id


def record_attempt(engine, run_id, brand_id, source, keyword, status, count, lease_token, error=None, post_ids=()):
    with Session(engine) as db, db.begin():
        active_run(db, run_id, lease_token, brand_id)
        attempt = TrackingAttempt(run_id=run_id, source=source, keyword=keyword, status=status,
                                  result_count=count, error_code=error)
        db.add(attempt)
        db.flush()
        db.add_all([AttemptPostMatch(attempt_id=attempt.id, post_id=post_id, run_id=run_id, brand_id=brand_id)
                    for post_id in set(post_ids)])


def finish(engine, run_id, status, lease_token, error_code=None):
    with Session(engine) as db, db.begin():
        run = active_run(db, run_id, lease_token)
        run.status, run.finished_at = status, now()
        run.error_code = error_code
        run.lease_token, run.lease_expires_at = None, None
        if status in ("success", "partial", "failed") and db.get(SentimentWork, run_id) is None:
            current = database_now(db)
            db.add(SentimentWork(run_id=run_id, status="pending", failures=0, next_attempt_at=current, updated_at=current))


def fail_queued(engine, run_id, error_code):
    """Kết thúc phiên còn chờ khi không thể chạy (ví dụ chưa cấu hình nguồn thu thập); phiên đã nhận/kết thúc giữ nguyên."""
    with Session(engine) as db, db.begin():
        run = db.scalar(select(TrackingRun).where(TrackingRun.id == run_id, TrackingRun.status == "queued").with_for_update())
        if run is None:
            return False
        run.status, run.finished_at, run.error_code = "failed", now(), error_code
        return True


def mark_stale(engine, older_than_minutes, requeue=False, max_recovery_attempts=1):
    """Đánh dấu lỗi phiên quá hạn và có thể xếp lại hữu hạn theo cấu hình."""
    if older_than_minutes < 30:
        raise ValueError("Thời hạn tối thiểu là 30 phút")
    if not isinstance(requeue, bool) or not 0 <= max_recovery_attempts <= 3:
        raise ValueError("Cấu hình phục hồi không hợp lệ")
    with Session(engine) as db, db.begin():
        current = database_now(db)
        cutoff = current - timedelta(minutes=older_than_minutes)
        runs = db.scalars(select(TrackingRun).where(TrackingRun.status == "running", or_(
            TrackingRun.lease_expires_at <= current,
            and_(TrackingRun.lease_expires_at.is_(None), TrackingRun.started_at < cutoff)))
                          .with_for_update(skip_locked=True)).all()
        for run in runs:
            run.status, run.finished_at, run.error_code = "failed", now(), "worker_timeout"
            run.lease_token, run.lease_expires_at = None, None
            if db.get(SentimentWork, run.id) is None:
                db.add(SentimentWork(run_id=run.id, status="pending", failures=0, next_attempt_at=current, updated_at=current))
            recovery_attempt = run.config_snapshot.get("recovery_attempt", 0)
            config = db.get(TrackingConfig, run.brand_id)
            if (requeue and type(recovery_attempt) is int and recovery_attempt < max_recovery_attempts
                    and config is not None and config.active):
                snapshot = {**run.config_snapshot, "recovery_attempt": recovery_attempt + 1,
                            "recovered_from": str(run.id)}
                replacement = TrackingRun(brand_id=run.brand_id, status="queued", queued_at=current,
                                          config_snapshot=snapshot)
                db.add(replacement)
                db.flush()
                db.add(TrackingOutbox(run_id=replacement.id))
        return len(runs)


def process(engine, run_id, brand_id, config, provider, lease_token):
    """Mỗi cặp nguồn/từ khóa là một lượt; provider phải giới hạn chi phí."""
    if isinstance(provider, FirecrawlTikTok):
        # Gia hạn trước từng trang và từng lần retry, không chỉ trước search/comments.
        provider.before_request = lambda: ensure_active(engine, run_id, brand_id, lease_token)
    heartbeat = LeaseHeartbeat(engine, run_id, brand_id, lease_token).start()
    outcomes = []
    saved_posts = 0
    comment_cache = {}
    try:
        for source in config["sources"]:
            for keyword in config["keywords"]:
                found = 0
                post_ids = []
                try:
                    if source != "tiktok":
                        raise ProviderError("unsupported_source")
                    ensure_active(engine, run_id, brand_id, lease_token)
                    raw_posts = provider.search(keyword)
                    records = (provider.normalize_posts(raw_posts) if hasattr(provider, "normalize_posts")
                               else ranked_posts(raw_posts))
                    if raw_posts and not records:
                        raise ProviderError("invalid_search_data")
                    if isinstance(provider, FirecrawlTikTok):
                        records = relevant_posts(records, keyword, config.get("brand_name"))
                    del raw_posts
                    comment_error = None
                    for post in records[:config["postLimit"]]:
                        cache_key = post["source_id"]
                        cached = comment_cache.get(cache_key) if cache_key else None
                        if cached is not None:
                            comments, error = cached
                        else:
                            ensure_active(engine, run_id, brand_id, lease_token)
                            try:
                                comments, error = provider.comments(post["url"]), None
                                comments = [{key: item.get(key) for key in ("cid", "text", "create_time", "digg_count")}
                                            for item in comments if isinstance(item, dict)]
                            except ProviderError as exc:
                                comments, error = [], exc.code
                            if cache_key:
                                comment_cache[cache_key] = (comments, error)
                        if error:
                            comment_error = error
                        post_ids.append(save_post(engine, run_id, brand_id, post, comments, lease_token))
                        found += 1
                        if comment_error in ("call_limit", "estimated_credit_limit", "daily_estimated_credit_limit"):
                            break
                    state = "failed" if comment_error else ("success" if found else "empty")
                    record_attempt(engine, run_id, brand_id, getattr(provider, "attempt_source", source), keyword, state, found, lease_token, comment_error, post_ids)
                except ProviderError as exc:
                    state = "failed"
                    record_attempt(engine, run_id, brand_id, getattr(provider, "attempt_source", source), keyword, state, found, lease_token, exc.code, post_ids)
                except RunNotActive:
                    raise
                except Exception:
                    state = "failed"
                    record_attempt(engine, run_id, brand_id, getattr(provider, "attempt_source", source), keyword, state, found, lease_token, "internal_error", post_ids)
                saved_posts += found
                outcomes.append(state)
        successful = sum(status in ("success", "empty") for status in outcomes)
        status = "success" if successful == len(outcomes) else ("partial" if successful or saved_posts else "failed")
        heartbeat.check()
        finish(engine, run_id, status, lease_token)
        return run_id, status
    except RunNotActive:
        raise
    except Exception:
        try:
            finish(engine, run_id, "failed", lease_token, "internal_error")
        except RunNotActive:
            pass
        raise
    finally:
        heartbeat.stop()


def run_once(engine, brand_id, provider):
    run_id, config = prepare(engine, brand_id)
    config.update(search_pages=getattr(provider, "search_pages", 1),
                  comment_pages=getattr(provider, "comment_pages", 1))
    if isinstance(provider, FirecrawlTikTok):
        config["relevance_filter"] = "caption-v1"
    with Session(engine) as db, db.begin():
        run = db.get(TrackingRun, run_id)
        lease_token = run.lease_token
        active_run(db, run_id, lease_token, brand_id).config_snapshot = config
    return process(engine, run_id, brand_id, config, provider, lease_token)


def run_queued(engine, run_id, provider):
    """Chỉ một worker được nhận phiên chờ; không xử lý lại phiên đã nhận."""
    with Session(engine) as db, db.begin():
        brand_id = db.scalar(select(TrackingRun.brand_id).where(TrackingRun.id == run_id))
        if brand_id is None:
            raise RunNotQueued("Phiên không tồn tại hoặc không còn chờ")
        db.scalar(select(Brand.id).where(Brand.id == brand_id).with_for_update())
        run = db.scalar(select(TrackingRun).where(TrackingRun.id == run_id).with_for_update())
        if run is None or run.status != "queued":
            raise RunNotQueued("Phiên không tồn tại hoặc không còn chờ")
        config = db.get(TrackingConfig, brand_id)
        if config is None or not config.active:
            run.status, run.finished_at, run.error_code = "skipped", now(), "tracking_paused"
            return run.id, "skipped"
        run.status = "running"
        run.started_at = database_now(db)
        run.lease_token = uuid4()
        run.lease_expires_at = run.started_at + lease_duration()
        snapshot = dict(run.config_snapshot)
        if isinstance(provider, FirecrawlTikTok):
            snapshot["relevance_filter"] = "caption-v1"
        snapshot.update(search_pages=getattr(provider, "search_pages", 1),
                        comment_pages=getattr(provider, "comment_pages", 1))
        run.config_snapshot = snapshot
        brand_id, lease_token = run.brand_id, run.lease_token
    return process(engine, run_id, brand_id, snapshot, provider, lease_token)

"""API thử nghiệm, xác thực Cognito bắt buộc cho các route nghiệp vụ."""
from typing import Annotated
from typing import Literal
from datetime import datetime
import os
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select, true
from sqlalchemy.orm import Session

from app.auth import current_subject
from app.config import cors_origins
from app.database import session
from app.models import AttemptPostMatch, Brand, BrandKeyword, BrandSource, Comment, EngagementSnapshot, Post, RunCommentMatch, RunPostMatch, TrackingAttempt, TrackingConfig, TrackingRun, User
from app.tracking import prepare
from app.scheduler import next_slot

app = FastAPI(title="Brand Auto-Tracking API", version="0.1.0")
origins = cors_origins(os.getenv("CORS_ORIGINS", ""))
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])


@app.get("/health", tags=["system"])
def health():
    """Kiểm tra tiến trình API; không kiểm tra kết nối database."""
    return {"status": "ok"}


class BrandCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200, pattern=r".*\S.*")


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


@app.get("/brands", response_model=list[BrandRead], tags=["brands"])
def list_brands(subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)],
                limit: Annotated[int, Query(ge=1, le=100)] = 50,
                offset: Annotated[int, Query(ge=0)] = 0):
    return db.scalars(select(Brand).join(User).where(User.cognito_sub == subject)
                      .order_by(Brand.name, Brand.id).limit(limit).offset(offset)).all()


@app.post("/brands", response_model=BrandRead, status_code=201, tags=["brands"])
def create_brand(body: BrandCreate, subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)],
                 idempotency_key: Annotated[UUID | None, Header(alias="Idempotency-Key")] = None):
    # Dùng upsert cho lần truy cập đầu đồng thời của cùng một Cognito sub.
    from sqlalchemy.dialects.postgresql import insert

    db.execute(insert(User).values(cognito_sub=subject).on_conflict_do_nothing(index_elements=[User.cognito_sub]))
    user_id = db.scalar(select(User.id).where(User.cognito_sub == subject))
    name = body.name.strip()
    if idempotency_key is None:
        brand = Brand(owner_id=user_id, name=name)
        db.add(brand)
    else:
        db.execute(insert(Brand).values(id=uuid4(), owner_id=user_id, name=name,
                                      create_request_key=idempotency_key, create_request_name=name)
                   .on_conflict_do_nothing(constraint="uq_brand_owner_create_key"))
        brand = db.scalar(select(Brand).where(Brand.owner_id == user_id, Brand.create_request_key == idempotency_key))
        if brand.create_request_name != name:
            raise HTTPException(status_code=409, detail="Idempotency key đã dùng với tên khác")
    db.commit()
    db.refresh(brand)
    return brand


class TrackingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    keywords: list[str] = Field(min_length=1, max_length=50)
    platforms: list[Literal["reddit", "threads", "facebook", "tiktok"]] = Field(min_length=1, max_length=4)
    frequency: Literal["daily", "twice-daily", "weekly"]
    run_time: str = Field(alias="runTime", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(min_length=1, max_length=64)
    post_limit: int = Field(alias="postLimit", ge=1, le=50, strict=True)
    active: bool = Field(strict=True)

    @field_validator("keywords")
    @classmethod
    def valid_keywords(cls, value):
        trimmed = [word.strip() for word in value]
        if any(not word or len(word) > 300 for word in trimmed) or len({word.casefold() for word in trimmed}) != len(trimmed):
            raise ValueError("Từ khóa phải khác nhau và không rỗng")
        return trimmed

    @field_validator("platforms")
    @classmethod
    def unique_platforms(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Nền tảng không được trùng")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Múi giờ không hợp lệ") from None
        return value


class TrackingRead(TrackingUpdate):
    next_run_at: datetime | None = Field(default=None, alias="nextRunAt")


def owned_brand(db: Session, subject: str, brand_id: UUID, lock: bool = False):
    query = select(Brand).join(User).where(Brand.id == brand_id, User.cognito_sub == subject)
    if lock:
        query = query.with_for_update(of=Brand)
    brand = db.scalar(query)
    if brand is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhãn hàng")
    return brand


@app.put("/brands/{brand_id}", response_model=BrandRead, tags=["brands"])
def rename_brand(brand_id: UUID, body: BrandCreate, subject: Annotated[str, Depends(current_subject)],
                 db: Annotated[Session, Depends(session)]):
    brand = owned_brand(db, subject, brand_id, lock=True)
    brand.name = body.name.strip()
    db.commit()
    db.refresh(brand)
    return brand


@app.put("/brands/{brand_id}/tracking", response_model=TrackingUpdate, tags=["brands"])
def update_tracking(brand_id: UUID, body: TrackingUpdate, subject: Annotated[str, Depends(current_subject)],
                    db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id, lock=True)
    config = db.get(TrackingConfig, brand_id)
    schedule_changed = (config is None or not config.active or config.frequency != body.frequency
                        or config.run_time != body.run_time or config.timezone != body.timezone)
    if config is None:
        config = TrackingConfig(brand_id=brand_id)
        db.add(config)
    config.frequency = body.frequency
    config.run_time = body.run_time
    config.timezone = body.timezone
    config.post_limit = body.post_limit
    config.active = body.active
    if not body.active:
        config.next_run_at = None
    elif schedule_changed:
        from datetime import timezone
        config.next_run_at = next_slot(datetime.now(timezone.utc), body.frequency, body.run_time, body.timezone)
    db.execute(delete(BrandKeyword).where(BrandKeyword.brand_id == brand_id))
    db.execute(delete(BrandSource).where(BrandSource.brand_id == brand_id))
    db.add_all([BrandKeyword(brand_id=brand_id, keyword=word) for word in body.keywords])
    db.add_all([BrandSource(brand_id=brand_id, source=source) for source in body.platforms])
    db.commit()
    return body


@app.get("/brands/{brand_id}/tracking", response_model=TrackingRead, tags=["brands"])
def read_tracking(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                  db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id)
    config = db.get(TrackingConfig, brand_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Chưa có cấu hình tracking")
    keywords = db.scalars(select(BrandKeyword.keyword).where(BrandKeyword.brand_id == brand_id).order_by(BrandKeyword.keyword)).all()
    platforms = db.scalars(select(BrandSource.source).where(BrandSource.brand_id == brand_id).order_by(BrandSource.source)).all()
    return TrackingRead(keywords=keywords, platforms=platforms, frequency=config.frequency, run_time=config.run_time,
                        timezone=config.timezone, post_limit=config.post_limit, active=config.active,
                        next_run_at=config.next_run_at)


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    status: str
    error_code: str | None


class RunQueued(BaseModel):
    id: UUID
    status: Literal["queued"]


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source: str
    keyword: str
    status: str
    result_count: int | None
    error_code: str | None


class CollectionLimits(BaseModel):
    search_pages: int
    comment_pages: int


class RunDetail(RunRead):
    attempts: list[AttemptRead]
    collection_limits: CollectionLimits | None


class MetricsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    captured_at: datetime
    likes: int | None
    comment_count: int | None
    views: int | None
    shares: int | None


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source: str
    source_id: str | None
    url: str
    title: str | None
    content: str | None
    posted_at: datetime | None
    first_seen_at: datetime
    maybe_duplicate: bool
    metrics: MetricsRead | None


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: str | None
    content: str
    posted_at: datetime | None
    maybe_duplicate: bool
    metrics: MetricsRead | None


class BrandOverview(BaseModel):
    post_count: int
    comment_count: int
    run_count: int
    latest_run: RunRead | None


@app.get("/brands/{brand_id}/overview", response_model=BrandOverview, tags=["tracking"])
def brand_overview(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                   db: Annotated[Session, Depends(session)]):
    """Tổng số bản ghi đã lưu, không suy đoán độ bao phủ hay cảm xúc."""
    owned_brand(db, subject, brand_id)
    post_count = db.scalar(select(func.count()).select_from(Post).where(Post.brand_id == brand_id))
    comment_count = db.scalar(select(func.count()).select_from(Comment).where(Comment.brand_id == brand_id))
    run_count = db.scalar(select(func.count()).select_from(TrackingRun).where(TrackingRun.brand_id == brand_id))
    latest = db.scalar(select(TrackingRun).where(TrackingRun.brand_id == brand_id)
                       .order_by(TrackingRun.queued_at.desc(), TrackingRun.id.desc()).limit(1))
    return BrandOverview(post_count=post_count, comment_count=comment_count, run_count=run_count, latest_run=latest)


def latest_metrics(db: Session, brand_id: UUID, *, post_id=None, comment_id=None, run_id=None):
    target = EngagementSnapshot.post_id == post_id if post_id else EngagementSnapshot.comment_id == comment_id
    statement = select(EngagementSnapshot).where(EngagementSnapshot.brand_id == brand_id, target)
    if run_id is not None:
        statement = statement.where(EngagementSnapshot.run_id == run_id)
    return db.scalar(statement.order_by(EngagementSnapshot.captured_at.desc(), EngagementSnapshot.id.desc()).limit(1))


def post_read(db: Session, brand_id: UUID, row: Post, run_id: UUID | None = None):
    return PostRead(id=row.id, source=row.source, source_id=row.source_id, url=row.url, title=row.title,
                    content=row.content, posted_at=row.posted_at, first_seen_at=row.first_seen_at,
                    maybe_duplicate=not bool(row.source_id),
                    metrics=latest_metrics(db, brand_id, post_id=row.id, run_id=run_id))


def filter_posted_time(query, column, posted_from, posted_until):
    if any(value is not None and (value.tzinfo is None or value.utcoffset() is None)
           for value in (posted_from, posted_until)):
        raise HTTPException(status_code=422, detail="Thời gian phải có múi giờ")
    if posted_from is not None and posted_until is not None and posted_from >= posted_until:
        raise HTTPException(status_code=422, detail="Khoảng thời gian không hợp lệ")
    if posted_from is not None:
        query = query.where(column >= posted_from)
    if posted_until is not None:
        query = query.where(column < posted_until)
    return query


def ranked_comments_query(brand_id: UUID, post_id: UUID, run_id: UUID | None = None):
    """Sắp theo lượt thích mới nhất; null đứng sau 0."""
    metrics = select(EngagementSnapshot.likes).where(
        EngagementSnapshot.brand_id == brand_id, EngagementSnapshot.comment_id == Comment.id)
    if run_id is not None:
        metrics = metrics.where(EngagementSnapshot.run_id == run_id)
    metrics = metrics.order_by(EngagementSnapshot.captured_at.desc(), EngagementSnapshot.id.desc()).limit(1).lateral("comment_metrics")
    statement = select(Comment).outerjoin(metrics, true()).where(Comment.brand_id == brand_id, Comment.post_id == post_id)
    if run_id is not None:
        statement = statement.join(RunCommentMatch, RunCommentMatch.comment_id == Comment.id).where(
            RunCommentMatch.brand_id == brand_id, RunCommentMatch.run_id == run_id)
    return statement.order_by(metrics.c.likes.desc().nullslast(), Comment.id)


def ranked_posts_query(brand_id: UUID, run_id: UUID | None = None):
    """Ưu tiên lượt thích khả dụng theo snapshot tương ứng; null đứng sau 0."""
    metrics = select(EngagementSnapshot.likes).where(
        EngagementSnapshot.brand_id == brand_id, EngagementSnapshot.post_id == Post.id)
    if run_id is not None:
        metrics = metrics.where(EngagementSnapshot.run_id == run_id)
    metrics = metrics.order_by(EngagementSnapshot.captured_at.desc(), EngagementSnapshot.id.desc()).limit(1).lateral("post_metrics")
    return (select(Post).outerjoin(metrics, true()).where(Post.brand_id == brand_id)
            .order_by(metrics.c.likes.desc().nullslast(), Post.first_seen_at.desc(), Post.id.desc()))


def owned_run(db: Session, brand_id: UUID, run_id: UUID):
    run = db.scalar(select(TrackingRun).where(TrackingRun.id == run_id, TrackingRun.brand_id == brand_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên")
    return run


@app.get("/brands/{brand_id}/runs", response_model=list[RunRead], tags=["tracking"])
def list_runs(brand_id: UUID, subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)],
              limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0):
    owned_brand(db, subject, brand_id)
    return db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id)
                      .order_by(TrackingRun.queued_at.desc(), TrackingRun.id.desc()).limit(limit).offset(offset)).all()


@app.post("/brands/{brand_id}/runs", response_model=RunQueued, status_code=202, tags=["tracking"])
def queue_run(brand_id: UUID, subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id)
    try:
        run_id, _ = prepare(db.get_bind(), brand_id, queued=True)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return RunQueued(id=run_id, status="queued")


@app.get("/brands/{brand_id}/runs/{run_id}", response_model=RunDetail, tags=["tracking"])
def read_run(brand_id: UUID, run_id: UUID, subject: Annotated[str, Depends(current_subject)],
             db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id)
    run = owned_run(db, brand_id, run_id)
    attempts = db.scalars(select(TrackingAttempt).where(TrackingAttempt.run_id == run_id)
                          .order_by(TrackingAttempt.source, TrackingAttempt.keyword, TrackingAttempt.id)).all()
    snapshot = run.config_snapshot
    search_pages, comment_pages = snapshot.get("search_pages"), snapshot.get("comment_pages")
    limits = (CollectionLimits(search_pages=search_pages, comment_pages=comment_pages)
              if type(search_pages) is int and type(comment_pages) is int else None)
    return RunDetail(id=run.id, queued_at=run.queued_at, started_at=run.started_at, finished_at=run.finished_at,
                     status=run.status, error_code=run.error_code, attempts=attempts, collection_limits=limits)


@app.get("/brands/{brand_id}/runs/{run_id}/mentions", response_model=list[PostRead], tags=["tracking"])
def list_run_mentions(brand_id: UUID, run_id: UUID, subject: Annotated[str, Depends(current_subject)],
                      db: Annotated[Session, Depends(session)], limit: Annotated[int, Query(ge=1, le=100)] = 50,
                      offset: Annotated[int, Query(ge=0)] = 0):
    owned_brand(db, subject, brand_id)
    owned_run(db, brand_id, run_id)
    rows = db.scalars(ranked_posts_query(brand_id, run_id).join(RunPostMatch, RunPostMatch.post_id == Post.id)
                      .where(RunPostMatch.brand_id == brand_id, RunPostMatch.run_id == run_id)
                      .limit(limit).offset(offset)).all()
    return [post_read(db, brand_id, row, run_id=run_id) for row in rows]


@app.get("/brands/{brand_id}/runs/{run_id}/mentions/{post_id}/comments", response_model=list[CommentRead], tags=["tracking"])
def list_run_comments(brand_id: UUID, run_id: UUID, post_id: UUID, subject: Annotated[str, Depends(current_subject)],
                      db: Annotated[Session, Depends(session)], limit: Annotated[int, Query(ge=1, le=100)] = 50,
                      offset: Annotated[int, Query(ge=0)] = 0,
                      posted_from: datetime | None = None, posted_until: datetime | None = None):
    owned_brand(db, subject, brand_id)
    owned_run(db, brand_id, run_id)
    if db.scalar(select(RunPostMatch.post_id).where(RunPostMatch.run_id == run_id,
                 RunPostMatch.post_id == post_id, RunPostMatch.brand_id == brand_id)) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết trong phiên")
    query = filter_posted_time(ranked_comments_query(brand_id, post_id, run_id), Comment.posted_at, posted_from, posted_until)
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return [CommentRead(id=row.id, source_id=row.source_id, content=row.content, posted_at=row.posted_at,
                        maybe_duplicate=not bool(row.source_id),
                        metrics=latest_metrics(db, brand_id, comment_id=row.id, run_id=run_id)) for row in rows]


@app.get("/brands/{brand_id}/runs/{run_id}/attempts/{attempt_id}/mentions", response_model=list[PostRead], tags=["tracking"])
def list_attempt_mentions(brand_id: UUID, run_id: UUID, attempt_id: UUID,
                          subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)],
                          limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0):
    owned_brand(db, subject, brand_id)
    owned_run(db, brand_id, run_id)
    if db.scalar(select(TrackingAttempt.id).where(TrackingAttempt.id == attempt_id, TrackingAttempt.run_id == run_id)) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt tracking")
    rows = db.scalars(ranked_posts_query(brand_id, run_id).join(AttemptPostMatch, AttemptPostMatch.post_id == Post.id)
                      .where(AttemptPostMatch.brand_id == brand_id, AttemptPostMatch.run_id == run_id,
                             AttemptPostMatch.attempt_id == attempt_id)
                      .limit(limit).offset(offset)).all()
    return [post_read(db, brand_id, row, run_id=run_id) for row in rows]


@app.get("/brands/{brand_id}/mentions", response_model=list[PostRead], tags=["tracking"])
def list_mentions(brand_id: UUID, subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)],
                  limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
                  source: Annotated[str | None, Query(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")] = None,
                  posted_from: datetime | None = None, posted_until: datetime | None = None):
    owned_brand(db, subject, brand_id)
    query = filter_posted_time(ranked_posts_query(brand_id), Post.posted_at, posted_from, posted_until)
    if source is not None:
        query = query.where(Post.source == source)
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return [post_read(db, brand_id, row) for row in rows]


@app.get("/brands/{brand_id}/mentions/{post_id}/comments", response_model=list[CommentRead], tags=["tracking"])
def list_comments(brand_id: UUID, post_id: UUID, subject: Annotated[str, Depends(current_subject)],
                  db: Annotated[Session, Depends(session)], limit: Annotated[int, Query(ge=1, le=100)] = 50,
                  offset: Annotated[int, Query(ge=0)] = 0,
                  posted_from: datetime | None = None, posted_until: datetime | None = None):
    owned_brand(db, subject, brand_id)
    if db.scalar(select(Post.id).where(Post.id == post_id, Post.brand_id == brand_id)) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    query = filter_posted_time(ranked_comments_query(brand_id, post_id), Comment.posted_at, posted_from, posted_until)
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return [CommentRead(id=row.id, source_id=row.source_id, content=row.content, posted_at=row.posted_at,
                        maybe_duplicate=not bool(row.source_id),
                        metrics=latest_metrics(db, brand_id, comment_id=row.id)) for row in rows]

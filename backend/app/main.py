"""API thử nghiệm, xác thực Cognito bắt buộc cho các route nghiệp vụ."""
from typing import Annotated
from typing import Literal
from datetime import datetime, timezone
import os
import re
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
from app.models import Alert, AlertRule, AnalysisJob, AttemptPostMatch, Brand, BrandKeyword, BrandSource, Comment, EngagementSnapshot, Post, RunCommentMatch, RunPostMatch, SentimentResult, SentimentWork, TrackingAttempt, TrackingConfig, TrackingOutbox, TrackingRun, User
from app.analysis import AnalysisRequestConflict, BedrockAnalysis, queue_positions, reconcile_stale_analyses, start_analysis
from app.alert_evaluation import evaluate_alert_rule
from app.sentiment import current_sentiment
from app.tracking import prepare
from app.scheduler import next_slot

app = FastAPI(title="Brand Auto-Tracking API", version="0.1.0")
origins = cors_origins(os.getenv("CORS_ORIGINS", ""))
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])


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


@app.delete("/brands/{brand_id}", tags=["brands"])
def delete_brand(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                 db: Annotated[Session, Depends(session)]):
    """Xóa dữ liệu trong database; từ chối khi tác vụ còn hoạt động."""
    brand = owned_brand(db, subject, brand_id, lock=True)
    run_ids = select(TrackingRun.id).where(TrackingRun.brand_id == brand_id)
    if (db.scalar(select(TrackingRun.id).where(TrackingRun.brand_id == brand_id,
                                                TrackingRun.status.in_(["queued", "running"])).limit(1)) or
            db.scalar(select(AnalysisJob.id).where(AnalysisJob.brand_id == brand_id,
                                                   AnalysisJob.status == "running").limit(1))):
        raise HTTPException(status_code=409, detail="Nhãn hàng đang có tác vụ hoạt động")
    work = db.scalars(select(SentimentWork).where(SentimentWork.run_id.in_(run_ids)).with_for_update()).all()
    if any(item.status == "running" for item in work):
        raise HTTPException(status_code=409, detail="Nhãn hàng đang có tác vụ hoạt động")
    for model in (Alert, AlertRule, AnalysisJob, SentimentResult, EngagementSnapshot,
                  RunCommentMatch, AttemptPostMatch, RunPostMatch, Comment, Post):
        db.execute(delete(model).where(model.brand_id == brand_id))
    for model in (SentimentWork, TrackingOutbox, TrackingAttempt):
        db.execute(delete(model).where(model.run_id.in_(run_ids)))
    db.execute(delete(TrackingRun).where(TrackingRun.brand_id == brand_id))
    for model in (TrackingConfig, BrandKeyword, BrandSource):
        db.execute(delete(model).where(model.brand_id == brand_id))
    db.delete(brand)
    db.commit()
    return {"deleted": True}


class AlertRecipients(BaseModel):
    model_config = ConfigDict(extra="forbid")
    emails: list[str] = Field(max_length=10)

    @field_validator("emails")
    @classmethod
    def validate_emails(cls, emails):
        cleaned = [email.strip().lower() for email in emails]
        if any(len(email) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", email) for email in cleaned):
            raise ValueError("Địa chỉ email không hợp lệ")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Địa chỉ email bị trùng")
        return cleaned


@app.get("/brands/{brand_id}/alert-recipients", response_model=AlertRecipients, tags=["alerts"])
def get_alert_recipients(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                         db: Annotated[Session, Depends(session)]):
    return {"emails": owned_brand(db, subject, brand_id).alert_emails}


@app.put("/brands/{brand_id}/alert-recipients", response_model=AlertRecipients, tags=["alerts"])
def put_alert_recipients(brand_id: UUID, body: AlertRecipients, subject: Annotated[str, Depends(current_subject)],
                         db: Annotated[Session, Depends(session)]):
    brand = owned_brand(db, subject, brand_id, lock=True)
    brand.alert_emails = body.emails
    db.commit()
    return body


class AlertRuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = Field(strict=True)
    growth_percent: int = Field(ge=0, le=1000, strict=True)
    window_days: int = Field(ge=1, le=90, strict=True)
    minimum_current: int = Field(ge=1, le=1000000, strict=True)
    absolute_threshold: int | None = Field(default=None, ge=1, le=1000000, strict=True)


class AlertRuleRead(AlertRuleUpdate):
    model_config = ConfigDict(from_attributes=True)
    content_type: Literal["post", "comment"]


@app.get("/brands/{brand_id}/alert-rules", response_model=list[AlertRuleRead], tags=["alerts"])
def list_alert_rules(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                     db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id)
    return db.scalars(select(AlertRule).where(AlertRule.brand_id == brand_id).order_by(AlertRule.content_type)).all()


@app.put("/brands/{brand_id}/alert-rules/{content_type}", response_model=AlertRuleRead, tags=["alerts"])
def put_alert_rule(brand_id: UUID, content_type: Literal["post", "comment"], body: AlertRuleUpdate,
                   subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id, lock=True)
    rule = db.get(AlertRule, (brand_id, content_type))
    if rule is None:
        rule = AlertRule(brand_id=brand_id, content_type=content_type)
        db.add(rule)
    for key, value in body.model_dump().items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    content_type: Literal["post", "comment"]
    window_start: datetime
    window_end: datetime
    previous_negative: int
    current_negative: int
    growth_percent: int
    minimum_current: int
    absolute_threshold: int | None
    reason: str
    created_at: datetime
    mode: Literal["window", "run"] = "window"
    run_id: UUID | None = None
    previous_total: int | None = None
    current_total: int | None = None
    notified_at: datetime | None = None


class TimelinePoint(BaseModel):
    run_id: UUID
    finished_at: datetime
    demo: bool
    demo_batch: int | None
    new_comments: int
    negative: int
    total: int
    unclassified: int
    alert_id: UUID | None


class TimelineRead(BaseModel):
    points: list[TimelinePoint]
    truncated: bool


class RunAlertEvaluationRead(BaseModel):
    status: Literal["triggered", "not_triggered", "insufficient_data", "disabled", "not_applicable"]
    reason: str
    run_id: UUID | None = None
    previous_negative: int | None = None
    previous_total: int | None = None
    current_negative: int | None = None
    current_total: int | None = None
    alert: AlertRead | None = None


@app.get("/brands/{brand_id}/sentiment-timeline", response_model=TimelineRead, tags=["alerts"])
def get_sentiment_timeline(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                           db: Annotated[Session, Depends(session)]):
    """Tỷ lệ bình luận tiêu cực lũy kế sau từng phiên thành công gần nhất."""
    owned_brand(db, subject, brand_id)
    from app.demo_alerts import sentiment_timeline
    return sentiment_timeline(db, brand_id)


@app.post("/brands/{brand_id}/alerts/evaluate-latest-run", response_model=RunAlertEvaluationRead, tags=["alerts"])
def evaluate_latest_run(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                        db: Annotated[Session, Depends(session)]):
    """Đánh giá lại phiên demo gần nhất; cảnh báo đã có được trả lại, không tạo bản sao."""
    owned_brand(db, subject, brand_id)
    from app.demo_alerts import evaluate_run_alert, latest_demo_run
    run = latest_demo_run(db, brand_id)
    db.rollback()
    if run is None:
        return RunAlertEvaluationRead(status="not_applicable", reason="no_demo_run")
    result = evaluate_run_alert(db.get_bind(), run.id)
    return RunAlertEvaluationRead(run_id=run.id, **{key: value for key, value in result.items() if key != "created"})


class AlertEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_end: datetime

    @field_validator("window_end")
    @classmethod
    def validate_end(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Thời gian phải có múi giờ")
        value = value.astimezone(timezone.utc)
        if value.time() != datetime.min.time() or value > datetime.now(timezone.utc):
            raise ValueError("Chỉ đánh giá cửa sổ đã kết thúc tại 00:00 UTC")
        return value


class AlertEvaluationRead(BaseModel):
    status: Literal["triggered", "not_triggered", "insufficient_data", "disabled"]
    reason: str
    previous_negative: int | None = None
    current_negative: int | None = None
    alert: AlertRead | None = None


@app.get("/brands/{brand_id}/alerts", response_model=list[AlertRead], tags=["alerts"])
def list_alerts(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                db: Annotated[Session, Depends(session)], limit: Annotated[int, Query(ge=1, le=100)] = 50,
                offset: Annotated[int, Query(ge=0)] = 0):
    owned_brand(db, subject, brand_id)
    return db.scalars(select(Alert).where(Alert.brand_id == brand_id)
                      .order_by(Alert.window_end.desc(), Alert.id.desc()).limit(limit).offset(offset)).all()


@app.post("/brands/{brand_id}/alert-rules/{content_type}/evaluate", response_model=AlertEvaluationRead, tags=["alerts"])
def evaluate_alert(brand_id: UUID, content_type: Literal["post", "comment"], body: AlertEvaluateRequest,
                   subject: Annotated[str, Depends(current_subject)], db: Annotated[Session, Depends(session)]):
    owned_brand(db, subject, brand_id)
    # Giải phóng kết nối kiểm tra quyền trước khi service mở giao dịch riêng.
    db.rollback()
    try:
        return AlertEvaluationRead(**evaluate_alert_rule(db.get_bind(), brand_id, content_type, body.window_end))
    except LookupError:
        raise HTTPException(status_code=404, detail="Chưa có quy tắc") from None


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_start: datetime
    window_end: datetime


class AnalysisEvidenceRead(BaseModel):
    id: str
    kind: Literal["post", "comment"]
    url: str
    observed_at: datetime
    content_hash: str
    text_truncated: bool
    # Đoạn trích đọc lúc trả kết quả (không lưu trong job); None nếu nội dung đã đổi khác bản AI đã đọc.
    text: str | None = None


class AnalysisFindingRead(BaseModel):
    summary: str
    recommendation: str
    evidence_ids: list[str]


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_key: UUID
    status: Literal["queued", "running", "success", "failed"]
    window_start: datetime
    window_end: datetime
    model_id: str
    created_at: datetime
    finished_at: datetime | None
    sample_count: int | None
    sample_truncated: bool | None
    has_undated_comments: bool | None
    evidence: list[AnalysisEvidenceRead] | None
    findings: list[AnalysisFindingRead] | None
    error_code: str | None
    # Số yêu cầu đang chờ trước yêu cầu này trên toàn hệ thống (chỉ khi `queued`).
    queue_position: int | None = None
    next_attempt_at: datetime | None = None


def analysis_provider(model_id: str):
    import boto3
    from botocore.config import Config
    client = boto3.client("bedrock-runtime", config=Config(connect_timeout=2, read_timeout=18,
                                                           retries={"total_max_attempts": 1}))
    return BedrockAnalysis(client, model_id)


@app.get("/brands/{brand_id}/analyses", response_model=list[AnalysisRead], tags=["analysis"])
def list_analyses(brand_id: UUID, subject: Annotated[str, Depends(current_subject)],
                  db: Annotated[Session, Depends(session)], limit: Annotated[int, Query(ge=1, le=100)] = 20,
                  offset: Annotated[int, Query(ge=0)] = 0):
    owned_brand(db, subject, brand_id)
    db.rollback()
    reconcile_stale_analyses(db.get_bind(), brand_id=brand_id)
    jobs = db.scalars(select(AnalysisJob).where(AnalysisJob.brand_id == brand_id)
                      .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc()).limit(limit).offset(offset)).all()
    return with_evidence_text(db, brand_id, jobs)


EVIDENCE_EXCERPT_CHARS = 300


def with_evidence_text(db: Session, brand_id: UUID, jobs) -> list[AnalysisRead]:
    """Gắn đoạn trích dẫn chứng của chính nhãn hàng, chỉ khi nội dung còn khớp hash bản AI đã đọc."""
    from app.sentiment import content_hash
    wanted = {"post": set(), "comment": set()}
    for job in jobs:
        for item in job.evidence or []:
            kind, _, raw = str(item.get("id", "")).partition(":")
            try:
                wanted[kind].add(UUID(raw))
            except (KeyError, ValueError):
                continue
    texts = {}
    for kind, model in (("post", Post), ("comment", Comment)):
        if wanted[kind]:
            for row_id, content in db.execute(select(model.id, model.content).where(
                    model.brand_id == brand_id, model.id.in_(wanted[kind]))):
                if content:
                    texts[f"{kind}:{row_id}"] = content
    result = []
    positions = queue_positions(db, jobs)
    for job in jobs:
        read = AnalysisRead.model_validate(job)
        read.queue_position = positions.get(job.id)
        if read.evidence:
            read.evidence = [item.model_copy(update={"text": texts[item.id][:EVIDENCE_EXCERPT_CHARS]})
                             if item.id in texts and content_hash(texts[item.id]) == item.content_hash else item
                             for item in read.evidence]
        result.append(read)
    return result


@app.post("/brands/{brand_id}/analyses", response_model=AnalysisRead, tags=["analysis"])
def create_analysis(brand_id: UUID, body: AnalysisRequest, subject: Annotated[str, Depends(current_subject)],
                    db: Annotated[Session, Depends(session)], request_key: Annotated[UUID, Header(alias="Idempotency-Key")]):
    owned_brand(db, subject, brand_id)
    db.rollback()
    if os.getenv("ANALYSIS_ENABLED", "false") != "true":
        raise HTTPException(status_code=503, detail="Phân tích AI chưa được bật")
    model_id = os.getenv("ANALYSIS_MODEL_ID", "")
    try:
        daily_limit = int(os.getenv("BEDROCK_DAILY_CALL_LIMIT", "0"))
        if not model_id or not 1 <= daily_limit <= 10000:
            raise ValueError("Thiếu cấu hình")
        provider = analysis_provider(model_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Phân tích AI chưa được cấu hình") from None
    try:
        job = start_analysis(db.get_bind(), brand_id, request_key, body.window_start, body.window_end,
                             model_id=model_id, daily_limit=daily_limit, provider=provider)
        return with_evidence_text(db, brand_id, [job])[0]
    except AnalysisRequestConflict:
        raise HTTPException(status_code=409, detail="Khóa yêu cầu đã dùng cho khoảng thời gian khác") from None
    except ValueError:
        raise HTTPException(status_code=422, detail="Khoảng thời gian không hợp lệ") from None
    except LookupError:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhãn hàng") from None


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
    sentiment: Literal["positive", "negative", "neutral", "unknown"]


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: str | None
    content: str
    posted_at: datetime | None
    maybe_duplicate: bool
    metrics: MetricsRead | None
    sentiment: Literal["positive", "negative", "neutral", "unknown"]


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
    result = db.scalar(select(SentimentResult).where(SentimentResult.brand_id == brand_id, SentimentResult.post_id == row.id))
    return PostRead(id=row.id, source=row.source, source_id=row.source_id, url=row.url, title=row.title,
                    content=row.content, posted_at=row.posted_at, first_seen_at=row.first_seen_at,
                    maybe_duplicate=not bool(row.source_id),
                    metrics=latest_metrics(db, brand_id, post_id=row.id, run_id=run_id),
                    sentiment=current_sentiment(result, row.content))


def comment_read(db: Session, brand_id: UUID, row: Comment, run_id: UUID | None = None):
    result = db.scalar(select(SentimentResult).where(SentimentResult.brand_id == brand_id, SentimentResult.comment_id == row.id))
    return CommentRead(id=row.id, source_id=row.source_id, content=row.content, posted_at=row.posted_at,
                       maybe_duplicate=not bool(row.source_id),
                       metrics=latest_metrics(db, brand_id, comment_id=row.id, run_id=run_id),
                       sentiment=current_sentiment(result, row.content))


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


@app.post("/brands/{brand_id}/runs/{run_id}/cancel", response_model=RunRead, tags=["tracking"])
def cancel_run(brand_id: UUID, run_id: UUID, subject: Annotated[str, Depends(current_subject)],
               db: Annotated[Session, Depends(session)]):
    # Cùng thứ tự khóa nhãn hàng rồi phiên như worker nhận việc.
    owned_brand(db, subject, brand_id, lock=True)
    run = db.scalar(select(TrackingRun).where(TrackingRun.id == run_id, TrackingRun.brand_id == brand_id).with_for_update())
    if run is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên")
    if run.status == "cancelled":
        return run
    if run.status != "queued":
        raise HTTPException(status_code=409, detail="Chỉ có thể hủy phiên đang chờ")
    run.status = "cancelled"
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


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
    return [comment_read(db, brand_id, row, run_id=run_id) for row in rows]


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
    return [comment_read(db, brand_id, row) for row in rows]

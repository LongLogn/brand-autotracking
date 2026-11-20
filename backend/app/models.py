"""Mô hình khởi đầu, chưa phải hợp đồng nghiệp vụ hoàn chỉnh."""
from uuid import UUID, uuid4

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    cognito_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class FirecrawlCreditReservation(Base):
    """Dự phòng credit ước tính chung cho mỗi ngày UTC và database."""
    __tablename__ = "firecrawl_credit_reservations"
    __table_args__ = (CheckConstraint("daily_limit >= 0 AND unit_estimate > 0 AND reserved >= 0 AND reserved <= daily_limit",
                                      name="ck_firecrawl_credit_reservation"),)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False)


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (UniqueConstraint("owner_id", "create_request_key", name="uq_brand_owner_create_key"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    create_request_key: Mapped[UUID | None] = mapped_column(Uuid)
    create_request_name: Mapped[str | None] = mapped_column(String(200))


class TrackingConfig(Base):
    __tablename__ = "tracking_configs"
    brand_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("brands.id"), primary_key=True)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    run_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    post_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BrandKeyword(Base):
    __tablename__ = "brand_keywords"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    brand_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("brands.id"), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(300), nullable=False)


class BrandSource(Base):
    __tablename__ = "brand_sources"
    brand_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("brands.id"), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), primary_key=True)


class TrackingRun(Base):
    __tablename__ = "tracking_runs"
    __table_args__ = (UniqueConstraint("id", "brand_id", name="uq_run_id_brand"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    brand_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("brands.id"), nullable=False, index=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)


class TrackingOutbox(Base):
    __tablename__ = "tracking_outbox"
    __table_args__ = (UniqueConstraint("run_id", name="uq_tracking_outbox_run"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("tracking_runs.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(100))


class TrackingAttempt(Base):
    __tablename__ = "tracking_attempts"
    __table_args__ = (UniqueConstraint("id", "run_id", name="uq_attempt_id_run"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("tracking_runs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_count: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("brand_id", "source", "source_id", name="uq_post_brand_source_id"),
                      UniqueConstraint("id", "brand_id", name="uq_post_id_brand"))
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    brand_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("brands.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("post_id", "source_id", name="uq_comment_post_source_id"),
                      UniqueConstraint("id", "brand_id", name="uq_comment_id_brand"),
                      UniqueConstraint("id", "post_id", "brand_id", name="uq_comment_id_post_brand"),
                      ForeignKeyConstraint(["post_id", "brand_id"], ["posts.id", "posts.brand_id"], name="fk_comment_post_brand"))
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    brand_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunPostMatch(Base):
    __tablename__ = "run_post_matches"
    __table_args__ = (UniqueConstraint("run_id", "post_id", "brand_id", name="uq_run_post_brand"),
                      ForeignKeyConstraint(["run_id", "brand_id"], ["tracking_runs.id", "tracking_runs.brand_id"], name="fk_run_post_run_brand"),
                      ForeignKeyConstraint(["post_id", "brand_id"], ["posts.id", "posts.brand_id"], name="fk_run_post_post_brand"))
    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    post_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    brand_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class RunCommentMatch(Base):
    __tablename__ = "run_comment_matches"
    __table_args__ = (ForeignKeyConstraint(["run_id", "brand_id"], ["tracking_runs.id", "tracking_runs.brand_id"], name="fk_run_comment_run_brand"),
                      ForeignKeyConstraint(["comment_id", "brand_id"], ["comments.id", "comments.brand_id"], name="fk_run_comment_comment_brand"),
                      ForeignKeyConstraint(["comment_id", "post_id", "brand_id"], ["comments.id", "comments.post_id", "comments.brand_id"], name="fk_run_comment_parent"),
                      ForeignKeyConstraint(["run_id", "post_id", "brand_id"], ["run_post_matches.run_id", "run_post_matches.post_id", "run_post_matches.brand_id"], name="fk_run_comment_run_post"))
    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    comment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    post_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    brand_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class AttemptPostMatch(Base):
    __tablename__ = "attempt_post_matches"
    __table_args__ = (ForeignKeyConstraint(["attempt_id", "run_id"], ["tracking_attempts.id", "tracking_attempts.run_id"], name="fk_attempt_post_attempt_run"),
                      ForeignKeyConstraint(["run_id", "brand_id"], ["tracking_runs.id", "tracking_runs.brand_id"], name="fk_attempt_post_run_brand"),
                      ForeignKeyConstraint(["post_id", "brand_id"], ["posts.id", "posts.brand_id"], name="fk_attempt_post_post_brand"))
    attempt_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    post_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    brand_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class EngagementSnapshot(Base):
    __tablename__ = "engagement_snapshots"
    __table_args__ = (CheckConstraint("(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)", name="ck_snapshot_one_target"),
                      ForeignKeyConstraint(["run_id", "brand_id"], ["tracking_runs.id", "tracking_runs.brand_id"], name="fk_snapshot_run_brand"),
                      ForeignKeyConstraint(["post_id", "brand_id"], ["posts.id", "posts.brand_id"], name="fk_snapshot_post_brand"),
                      ForeignKeyConstraint(["comment_id", "brand_id"], ["comments.id", "comments.brand_id"], name="fk_snapshot_comment_brand"))
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    brand_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    post_id: Mapped[UUID | None] = mapped_column(Uuid)
    comment_id: Mapped[UUID | None] = mapped_column(Uuid)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    likes: Mapped[int | None] = mapped_column(Integer)
    comment_count: Mapped[int | None] = mapped_column(Integer)
    views: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)

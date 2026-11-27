"""Thu thập bằng chứng so sánh hai cửa sổ cho cảnh báo.

Chỉ trả số lượng khi chứng minh được lịch, lượt thu thập và phiên bản phân loại.
Chưa ghi cảnh báo; dữ liệu cũ thiếu thời điểm quan sát được xử lý bảo thủ.
"""
from dataclasses import dataclass
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import product
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import (SENTIMENT_ALGORITHM_VERSION, Alert, AlertRule, Brand, Comment, Post, RunCommentMatch, RunPostMatch, SentimentResult,
                        TrackingAttempt, TrackingRun)
from app.alert_rules import evaluate_increase
from app.scheduler import next_slot
from app.sentiment import content_hash

MAX_EVIDENCE_ROWS = 5000


@dataclass(frozen=True)
class ComparisonEvidence:
    status: str
    reason: str
    previous_negative: int | None = None
    current_negative: int | None = None


def _scope(snapshot):
    if not isinstance(snapshot, dict):
        return None
    keywords, sources = snapshot.get("keywords"), snapshot.get("sources")
    if (not isinstance(keywords, list) or not isinstance(sources, list) or not keywords or not sources or
            any(not isinstance(v, str) or not v for v in keywords + sources) or
            len(set(keywords)) != len(keywords) or len(set(sources)) != len(sources)):
        return None
    fields = (snapshot.get("frequency"), snapshot.get("runTime"), snapshot.get("timezone"),
              snapshot.get("postLimit"), snapshot.get("search_pages"), snapshot.get("comment_pages"))
    frequency, run_time, zone, post_limit, search_pages, comment_pages = fields
    if (frequency not in ("daily", "twice-daily", "weekly") or not isinstance(run_time, str) or
            not isinstance(zone, str) or type(post_limit) is not int or not 1 <= post_limit <= 50 or
            type(search_pages) is not int or not 1 <= search_pages <= 3 or
            type(comment_pages) is not int or not 1 <= comment_pages <= 3):
        return None
    return (tuple(sorted(keywords)), tuple(sorted(sources)), *fields)


def _scheduled_for(snapshot):
    try:
        value = datetime.fromisoformat(snapshot["scheduled_for"])
        return value.astimezone(timezone.utc) if value.tzinfo is not None and value.utcoffset() is not None else None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def collect_comparison(engine, brand_id: UUID, content_type: str, previous_start: datetime,
                       current_start: datetime, current_end: datetime, *, db_session: Session | None = None) -> ComparisonEvidence:
    """Đếm nội dung tiêu cực duy nhất theo quan sát đầu tiên trong hai cửa sổ UTC.

    Các cửa sổ gồm đầu, không gồm cuối; mọi lần chạy theo lịch phải đủ bằng chứng.
    Không dùng kết quả khi thiếu ID, phiên bản, nhãn hoặc lịch. Giới hạn truy vấn
    để một nhãn hàng lớn không làm tiến trình chiếm bộ nhớ vô hạn.
    """
    insufficient = lambda reason: ComparisonEvidence("insufficient_data", reason)
    times = (previous_start, current_start, current_end)
    if (content_type not in ("post", "comment") or any(not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None for t in times)):
        raise ValueError("Cửa sổ không hợp lệ")
    previous_start, current_start, current_end = (t.astimezone(timezone.utc) for t in times)
    length = current_start - previous_start
    if not timedelta(0) < length <= timedelta(days=90) or current_end - current_start != length:
        raise ValueError("Cửa sổ không hợp lệ")
    with (nullcontext(db_session) if db_session is not None else Session(engine)) as db:
        # Mọi truy vấn bằng chứng trong cùng một ảnh chụp nhất quán.
        if db_session is None:
            db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        # Lấy tất cả phiên kể từ đầu khoảng; một phiên xếp muộn vẫn có thể có scheduled_for trong khoảng.
        runs = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id,
                          TrackingRun.queued_at >= previous_start).limit(MAX_EVIDENCE_ROWS + 1)).all()
        if len(runs) > MAX_EVIDENCE_ROWS:
            return insufficient("too_many_runs")
        scheduled = []
        for run in runs:
            slot = _scheduled_for(run.config_snapshot)
            if slot is not None and previous_start <= slot < current_end:
                scheduled.append((slot, run))
        if not scheduled:
            return insufficient("missing_schedule_evidence")
        scope = _scope(scheduled[0][1].config_snapshot)
        if scope is None:
            return insufficient("invalid_scope")
        if any(_scope(run.config_snapshot) != scope for _, run in scheduled):
            return insufficient("scope_changed")
        keywords, sources, frequency, run_time, zone, *_ = scope
        try:
            weekday = scheduled[0][0].astimezone(ZoneInfo(zone)).weekday()
            expected = []
            cursor = previous_start - timedelta(microseconds=1)
            while True:
                cursor = next_slot(cursor, frequency, run_time, zone, weekday)
                if cursor >= current_end:
                    break
                expected.append(cursor)
                if len(expected) > MAX_EVIDENCE_ROWS:
                    return insufficient("too_many_slots")
        except (ValueError, KeyError, OverflowError):
            return insufficient("invalid_schedule")
        slots = [slot for slot, _ in scheduled]
        if (not any(slot < current_start for slot in expected) or not any(slot >= current_start for slot in expected) or
                set(slots) != set(expected) or len(slots) != len(expected)):
            return insufficient("missing_scheduled_runs")
        if any(run.status != "success" or run.queued_at < slot or run.queued_at - slot > timedelta(minutes=15)
               for slot, run in scheduled):
            return insufficient("failed_or_late_run")
        by_id = {run.id: run for _, run in scheduled}
        attempts = db.scalars(select(TrackingAttempt).where(TrackingAttempt.run_id.in_(by_id))).all()
        pairs = set(product(sources, keywords))
        for run_id in by_id:
            rows = [a for a in attempts if a.run_id == run_id]
            if (len(rows) != len(pairs) or {(a.source, a.keyword) for a in rows} != pairs or
                    any(a.status not in ("success", "empty") for a in rows)):
                return insufficient("failed_or_missing_attempt")
        if content_type == "post":
            match, model = RunPostMatch, Post
            target_id = match.post_id
        else:
            match, model = RunCommentMatch, Comment
            target_id = match.comment_id
        rows = db.execute(select(match, model, SentimentResult, TrackingRun)
                          .join(model, model.id == target_id)
                          .join(TrackingRun, TrackingRun.id == match.run_id)
                          .outerjoin(SentimentResult, (SentimentResult.post_id == model.id if content_type == "post"
                                                     else SentimentResult.comment_id == model.id))
                          .where(match.brand_id == brand_id).limit(MAX_EVIDENCE_ROWS + 1)).all()
        if len(rows) > MAX_EVIDENCE_ROWS:
            return insufficient("too_many_observations")
        first = {}
        for match_row, item, result, run in rows:
            if match_row.observed_at is None:
                # Một quan sát cũ có thể chứng minh trước khoảng nếu phiên đã kết thúc trước khoảng.
                if run.finished_at is None or run.finished_at >= previous_start:
                    return insufficient("missing_observation_time")
                first[item.id] = (None, match_row, item, result, run)
            elif (item.id in first and first[item.id][0] == match_row.observed_at and
                  first[item.id][1].content_hash != match_row.content_hash):
                return insufficient("ambiguous_first_observation")
            elif item.id not in first or (first[item.id][0] is not None and match_row.observed_at < first[item.id][0]):
                first[item.id] = (match_row.observed_at, match_row, item, result, run)
        counts = [0, 0]
        model_ids = set()
        for observed_at, match_row, item, result, run in first.values():
            if observed_at is None or observed_at < previous_start or observed_at >= current_end:
                continue
            if run.id not in by_id:
                return insufficient("unmatched_observation_scope")
            if (not item.source_id or not item.content or not match_row.content_hash or result is None or
                    match_row.content_hash != content_hash(item.content) or result.content_hash != match_row.content_hash or
                    result.classifier_version != SENTIMENT_ALGORITHM_VERSION or result.label not in ("positive", "negative", "neutral")):
                return insufficient("missing_identity_or_classification")
            model_ids.add(result.model_id)
            if result.label == "negative":
                counts[int(observed_at >= current_start)] += 1
        if len(model_ids) > 1:
            return insufficient("classification_model_changed")
        return ComparisonEvidence("comparable", "complete", counts[0], counts[1])


def evaluate_alert_rule(engine, brand_id: UUID, content_type: str, window_end: datetime) -> dict:
    """Tính và lưu tối đa một cảnh báo cho quy tắc/cửa sổ trong giao dịch."""
    if (content_type not in ("post", "comment") or not isinstance(window_end, datetime) or
            window_end.tzinfo is None or window_end.utcoffset() is None):
        raise ValueError("Cửa sổ không hợp lệ")
    window_end = window_end.astimezone(timezone.utc)
    if window_end.time() != datetime.min.time() or window_end > datetime.now(timezone.utc):
        raise ValueError("Chỉ đánh giá cửa sổ đã kết thúc tại 00:00 UTC")
    for attempt in range(3):
        try:
            return _evaluate_alert_once(engine, brand_id, content_type, window_end)
        except DBAPIError as exc:
            error = exc.orig
            code = getattr(error, "sqlstate", None)
            constraint = getattr(getattr(error, "diag", None), "constraint_name", None)
            if attempt == 2 or not (code == "40001" or (code == "23505" and constraint == "uq_alert_window")):
                raise
    raise RuntimeError("Không thể đánh giá cảnh báo")


def _evaluate_alert_once(engine, brand_id, content_type, window_end):
    with Session(engine, expire_on_commit=False) as db, db.begin():
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        # Khóa theo cùng thứ tự với API sửa cấu hình, đảm bảo chống lặp đồng thời.
        brand = db.scalar(select(Brand).where(Brand.id == brand_id).with_for_update())
        rule = db.get(AlertRule, (brand_id, content_type))
        if brand is None or rule is None:
            raise LookupError("Chưa có quy tắc")
        existing = db.scalar(select(Alert).where(Alert.brand_id == brand_id, Alert.content_type == content_type,
                                                 Alert.window_end == window_end))
        if existing is not None:
            return {"status": "triggered", "reason": existing.reason, "previous_negative": existing.previous_negative,
                    "current_negative": existing.current_negative, "alert": existing}
        if not rule.enabled:
            return {"status": "disabled", "reason": "rule_disabled"}
        current_start = window_end - timedelta(days=rule.window_days)
        previous_start = current_start - timedelta(days=rule.window_days)
        evidence = collect_comparison(engine, brand_id, content_type, previous_start, current_start, window_end, db_session=db)
        if evidence.status != "comparable":
            return {"status": "insufficient_data", "reason": evidence.reason}
        decision = evaluate_increase(evidence.previous_negative, evidence.current_negative,
                                     growth_percent=Decimal(rule.growth_percent), minimum_current=rule.minimum_current,
                                     absolute_threshold=rule.absolute_threshold, comparable=True, fully_classified=True)
        result = {"status": decision.status, "reason": decision.reason,
                  "previous_negative": evidence.previous_negative, "current_negative": evidence.current_negative}
        if decision.status == "triggered":
            alert = Alert(brand_id=brand_id, content_type=content_type, window_start=current_start, window_end=window_end,
                          previous_negative=evidence.previous_negative, current_negative=evidence.current_negative,
                          growth_percent=rule.growth_percent, minimum_current=rule.minimum_current,
                          absolute_threshold=rule.absolute_threshold, reason=decision.reason)
            db.add(alert)
            db.flush()
            result["alert"] = alert
        return result

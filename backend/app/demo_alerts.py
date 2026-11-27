"""Cảnh báo theo tỷ lệ tiêu cực lũy kế giữa hai lần thu thập demo liên tiếp.

Chỉ áp dụng cho phiên có `demo_session`; nhãn cảm xúc là nhãn giả lập gán theo câu
mẫu (model `demo-fixture-labels`), không phải kết quả Bedrock. Logic cảnh báo theo
cửa sổ ngày cho dữ liệu thật nằm ở `alert_evaluation` và không bị thay đổi.
"""
import json
import os
import unicodedata
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.demo_stream import demo_label
from app.models import (SENTIMENT_ALGORITHM_VERSION, Alert, AlertRule, Brand, Comment, RunCommentMatch, SentimentResult,
                        SentimentWork, TrackingRun)
from app.sentiment import content_hash

DEMO_MODEL_ID = "demo-fixture-labels"
MAX_TIMELINE_RUNS = 50
MAX_TIMELINE_ROWS = 20000


def _is_demo(run):
    return run is not None and isinstance(run.config_snapshot, dict) and run.config_snapshot.get("demo_session") is not None


def label_demo_run(engine, run_id: UUID) -> int:
    """Gán nhãn giả lập cho bình luận của một phiên demo; trả số nhãn đã ghi."""
    with Session(engine) as db, db.begin():
        run = db.get(TrackingRun, run_id)
        if not _is_demo(run):
            raise ValueError("Chỉ gán nhãn giả lập cho phiên demo")
        rows = db.execute(select(Comment).join(RunCommentMatch, RunCommentMatch.comment_id == Comment.id)
                          .where(RunCommentMatch.run_id == run_id)).scalars().all()
        written = 0
        current = datetime.now(timezone.utc)
        for comment in rows:
            label = demo_label(comment.content)
            if label is None:
                continue
            digest = content_hash(comment.content)
            result = db.scalar(select(SentimentResult).where(SentimentResult.comment_id == comment.id))
            if result is None:
                db.add(SentimentResult(brand_id=comment.brand_id, comment_id=comment.id, content_hash=digest, label=label,
                                       model_id=DEMO_MODEL_ID, classifier_version=SENTIMENT_ALGORITHM_VERSION, classified_at=current))
            else:
                result.content_hash, result.label, result.model_id = digest, label, DEMO_MODEL_ID
                result.classifier_version, result.classified_at = SENTIMENT_ALGORITHM_VERSION, current
            written += 1
        work = db.get(SentimentWork, run_id)
        if work is not None and work.status == "pending":
            # Phiên demo đã có nhãn giả lập; không gửi sang Bedrock.
            work.status, work.updated_at = "complete", current
        return written


def _cumulative(db, brand_id, run_ids):
    """Đếm bình luận duy nhất và số tiêu cực theo nhãn hiện tại trong các phiên."""
    if not run_ids:
        return 0, 0, 0
    rows = db.execute(select(Comment.id, Comment.content, SentimentResult)
                      .join(RunCommentMatch, RunCommentMatch.comment_id == Comment.id)
                      .outerjoin(SentimentResult, SentimentResult.comment_id == Comment.id)
                      .where(RunCommentMatch.brand_id == brand_id, RunCommentMatch.run_id.in_(run_ids))
                      .limit(MAX_TIMELINE_ROWS + 1)).all()
    if len(rows) > MAX_TIMELINE_ROWS:
        raise ValueError("Quá nhiều bình luận để tính tỷ lệ")
    seen = {}
    for comment_id, content, result in rows:
        seen[comment_id] = (content, result)
    negative = unknown = 0
    for content, result in seen.values():
        valid = (result is not None and result.classifier_version == SENTIMENT_ALGORITHM_VERSION
                 and result.content_hash == content_hash(content) and result.label in ("positive", "negative", "neutral"))
        if not valid:
            unknown += 1
        elif result.label == "negative":
            negative += 1
    return negative, len(seen), unknown


def ratio_increase(previous_negative, previous_total, current_negative, current_total, growth_percent, minimum_current,
                   absolute_threshold=None):
    """So tỷ lệ tiêu cực lũy kế; dùng số nguyên để tránh sai số làm tròn."""
    if previous_total <= 0 or current_total <= 0:
        return "insufficient_data", "missing_total"
    if previous_negative == 0:
        if absolute_threshold is None:
            return "insufficient_data", "zero_baseline"
        triggered = current_negative >= max(absolute_threshold, minimum_current)
        return ("triggered" if triggered else "not_triggered"), "absolute_threshold"
    # (cur/ct - prev/pt) / (prev/pt) >= growth/100  <=>  (cur*pt - prev*ct) * 100 >= growth * prev * ct
    growth = (current_negative * previous_total - previous_negative * current_total) * 100
    triggered = current_negative >= minimum_current and growth >= growth_percent * previous_negative * current_total
    return ("triggered" if triggered else "not_triggered"), "ratio_growth"


def _session_runs(db, run):
    session = run.config_snapshot.get("demo_session")
    runs = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == run.brand_id, TrackingRun.status == "success")).all()
    return sorted((item for item in runs if item.config_snapshot.get("demo_session") == session
                   and type(item.config_snapshot.get("demo_batch")) is int),
                  key=lambda item: item.config_snapshot["demo_batch"])


def evaluate_run_alert(engine, run_id: UUID) -> dict:
    """Đánh giá và lưu tối đa một cảnh báo cho một phiên demo đã thành công."""
    for attempt in range(3):
        try:
            return _evaluate_run_once(engine, run_id)
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if attempt == 2 or code not in ("40001", "23505"):
                raise
    raise RuntimeError("Không thể đánh giá cảnh báo")


def _alert_result(alert):
    return {"status": "triggered", "reason": alert.reason, "previous_negative": alert.previous_negative,
            "current_negative": alert.current_negative, "previous_total": alert.previous_total,
            "current_total": alert.current_total, "alert": alert, "created": False}


def _evaluate_run_once(engine, run_id):
    with Session(engine, expire_on_commit=False) as db, db.begin():
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        run = db.get(TrackingRun, run_id)
        if not _is_demo(run):
            return {"status": "not_applicable", "reason": "not_demo_run"}
        # Khóa nhãn hàng theo cùng thứ tự với API sửa quy tắc.
        db.scalar(select(Brand).where(Brand.id == run.brand_id).with_for_update())
        rule = db.get(AlertRule, (run.brand_id, "comment"))
        existing = db.scalar(select(Alert).where(Alert.run_id == run_id, Alert.content_type == "comment"))
        if existing is not None:
            return _alert_result(existing)
        if rule is None or not rule.enabled:
            return {"status": "disabled", "reason": "rule_disabled"}
        if run.status != "success":
            return {"status": "insufficient_data", "reason": "run_not_successful"}
        runs = _session_runs(db, run)
        batch = run.config_snapshot.get("demo_batch")
        earlier = [item for item in runs if item.config_snapshot["demo_batch"] < batch]
        if not earlier:
            return {"status": "insufficient_data", "reason": "baseline"}
        previous = earlier[-1]
        pn, pt, pu = _cumulative(db, run.brand_id, [item.id for item in earlier])
        cn, ct, cu = _cumulative(db, run.brand_id, [item.id for item in earlier] + [run.id])
        result = {"previous_negative": pn, "previous_total": pt, "current_negative": cn, "current_total": ct}
        if pu or cu:
            return {"status": "insufficient_data", "reason": "missing_classification", **result}
        status, reason = ratio_increase(pn, pt, cn, ct, rule.growth_percent, rule.minimum_current, rule.absolute_threshold)
        result.update(status=status, reason=reason)
        if status == "triggered":
            alert = Alert(brand_id=run.brand_id, content_type="comment", mode="run", run_id=run.id,
                          window_start=previous.finished_at, window_end=run.finished_at,
                          previous_negative=pn, current_negative=cn, previous_total=pt, current_total=ct,
                          growth_percent=rule.growth_percent, minimum_current=rule.minimum_current,
                          absolute_threshold=rule.absolute_threshold, reason=reason)
            db.add(alert)
            db.flush()
            result.update(alert=alert, created=True)
        return result


def latest_demo_run(db, brand_id):
    runs = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id, TrackingRun.status == "success")
                      .order_by(TrackingRun.finished_at.desc()).limit(MAX_TIMELINE_RUNS)).all()
    return next((run for run in runs if _is_demo(run)), None)


def sentiment_timeline(db, brand_id):
    """Diễn biến lũy kế theo từng phiên thành công gần nhất (tối đa 50 phiên)."""
    runs = db.scalars(select(TrackingRun).where(TrackingRun.brand_id == brand_id, TrackingRun.status == "success")
                      .order_by(TrackingRun.finished_at.desc()).limit(MAX_TIMELINE_RUNS)).all()
    runs = sorted(runs, key=lambda item: item.finished_at)
    rows = db.execute(select(RunCommentMatch.run_id, Comment.id, Comment.content, SentimentResult)
                      .join(Comment, Comment.id == RunCommentMatch.comment_id)
                      .outerjoin(SentimentResult, SentimentResult.comment_id == Comment.id)
                      .where(RunCommentMatch.brand_id == brand_id, RunCommentMatch.run_id.in_([run.id for run in runs]))
                      .limit(MAX_TIMELINE_ROWS + 1)).all() if runs else []
    truncated = len(rows) > MAX_TIMELINE_ROWS
    by_run = {}
    for run_id, comment_id, content, result in rows[:MAX_TIMELINE_ROWS]:
        by_run.setdefault(run_id, {})[comment_id] = (content, result)
    alerts = {alert.run_id: alert for alert in db.scalars(select(Alert).where(
        Alert.brand_id == brand_id, Alert.mode == "run", Alert.run_id.in_([run.id for run in runs]))).all()} if runs else {}
    seen, points = set(), []
    negative = unknown = 0
    for run in runs:
        new = 0
        for comment_id, (content, result) in by_run.get(run.id, {}).items():
            if comment_id in seen:
                continue
            seen.add(comment_id)
            new += 1
            valid = (result is not None and result.classifier_version == SENTIMENT_ALGORITHM_VERSION
                     and result.content_hash == content_hash(content) and result.label in ("positive", "negative", "neutral"))
            if not valid:
                unknown += 1
            elif result.label == "negative":
                negative += 1
        alert = alerts.get(run.id)
        points.append({"run_id": run.id, "finished_at": run.finished_at, "demo": _is_demo(run),
                       "demo_batch": run.config_snapshot.get("demo_batch") if _is_demo(run) else None,
                       "new_comments": new, "negative": negative, "total": len(seen), "unclassified": unknown,
                       "alert_id": alert.id if alert else None})
    return {"points": points, "truncated": truncated}


def alert_message(alert, brand_name, base_url):
    previous = alert.previous_negative * 100 / alert.previous_total
    current = alert.current_negative * 100 / alert.current_total
    link = f"{base_url.rstrip('/')}/?brand={alert.brand_id}&alert={alert.id}"
    name = "".join(ch for ch in brand_name if ch.isprintable())[:60]
    # Tiêu đề email chỉ dùng ASCII để tránh lỗi mã hóa ở dịch vụ gửi.
    ascii_name = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = "".join(ch for ch in ascii_name if 32 <= ord(ch) < 127).strip() or "nhan hang"
    subject = f"Canh bao {ascii_name}: binh luan tieu cuc tang"[:99]
    body = (f"[DEMO] Cảnh báo nhãn hàng {name}\n\n"
            f"Tỷ lệ bình luận tiêu cực tăng từ {previous:.0f}% ({alert.previous_negative}/{alert.previous_total}) "
            f"lên {current:.0f}% ({alert.current_negative}/{alert.current_total}), "
            f"vượt ngưỡng tăng {alert.growth_percent}%.\n\n"
            f"Xem chi tiết: {link}\n\n"
            "Dữ liệu trong kịch bản demo là dữ liệu giả lập. Email này gửi đến hộp thư cố định của nhóm demo.")
    return subject, body


def notify_alert(engine, alert_id: UUID, publish, base_url: str) -> bool:
    """Gửi tối đa một thông báo cho cảnh báo; trả True khi đã gửi trong lần gọi này.

    Đánh dấu trước rồi mới gửi; nếu gửi lỗi thì bỏ đánh dấu để lần sau thử lại.
    """
    with Session(engine, expire_on_commit=False) as db, db.begin():
        claimed = db.execute(update(Alert).where(Alert.id == alert_id, Alert.notified_at.is_(None))
                             .values(notified_at=datetime.now(timezone.utc)).returning(Alert.id)).scalar()
        if claimed is None:
            return False
        alert = db.get(Alert, alert_id)
        brand = db.get(Brand, alert.brand_id)
        subject, body = alert_message(alert, brand.name if brand else "", base_url)
    try:
        publish(subject, body)
    except Exception:
        with Session(engine) as db, db.begin():
            db.execute(update(Alert).where(Alert.id == alert_id).values(notified_at=None))
        raise
    return True


def sns_publisher():
    topic = os.environ.get("ALERT_TOPIC_ARN", "")
    if not topic:
        return None
    import boto3
    client = boto3.client("sns")
    return lambda subject, body: client.publish(TopicArn=topic, Subject=subject, Message=body)


def process_demo_run(engine, run_id: UUID) -> dict:
    """Sau một phiên demo thành công: gán nhãn giả lập, đánh giá cảnh báo, gửi email."""
    labeled = label_demo_run(engine, run_id)
    result = evaluate_run_alert(engine, run_id)
    sent = False
    alert = result.get("alert")
    if alert is not None:
        publish = sns_publisher()
        base_url = os.environ.get("APP_BASE_URL", "")
        if publish is not None and base_url:
            sent = notify_alert(engine, alert.id, publish, base_url)
    print(json.dumps({"event": "demo_alert_evaluation", "run_id": str(run_id), "labeled": labeled,
                      "status": result["status"], "reason": result["reason"],
                      "previous": [result.get("previous_negative"), result.get("previous_total")],
                      "current": [result.get("current_negative"), result.get("current_total")],
                      "notified": sent, "alert": 0}))
    return {**result, "labeled": labeled, "notified": sent}

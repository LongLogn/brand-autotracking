"""Worker Lambda xử lý tối đa một phiên đã xếp trong mỗi lần gọi."""
import json
import os
from datetime import datetime, timezone
from functools import partial
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.firecrawl import FirecrawlTikTok, reserve_daily_credits
from app.models import AlertRule, TrackingOutbox, TrackingRun
from app.alert_evaluation import evaluate_alert_rule
from app.analysis import reconcile_stale_analyses
from app.outbox import count_exhausted, publish_pending
from app.tracking import RunNotQueued, mark_stale, run_queued
from app.scheduler import enqueue_due
from app.sentiment import (BedrockSentimentClassifier, check_sentiment_lease, claim_sentiment_work, count_failed_sentiment_work,
                           classify_run, finish_sentiment_work)
from app.worker import work_once


def provider():
    import boto3

    secret_id = os.environ["FIRECRAWL_SECRET_ARN"]
    secret = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)
    value = json.loads(secret["SecretString"])
    key = value.get("api_key")
    if not isinstance(key, str) or not key:
        raise ValueError("Invalid Firecrawl secret")
    daily_budget = int(os.environ.get("WORKER_DAILY_ESTIMATED_CREDIT_BUDGET", "0"))
    reserve_daily = partial(reserve_daily_credits, engine(), daily_budget)
    return FirecrawlTikTok(key, max_calls=int(os.environ.get("WORKER_MAX_CALLS", "2")),
                          max_attempts=int(os.environ.get("WORKER_MAX_ATTEMPTS", "1")),
                          search_pages=int(os.environ.get("WORKER_SEARCH_PAGES", "1")),
                          comment_pages=int(os.environ.get("WORKER_COMMENT_PAGES", "1")),
                          estimated_credit_budget=int(os.environ["WORKER_ESTIMATED_CREDIT_BUDGET"])
                          if os.environ.get("WORKER_ESTIMATED_CREDIT_BUDGET", "") else None,
                          estimated_credits_per_call=int(os.environ.get("WORKER_ESTIMATED_CREDITS_PER_CALL", "2")),
                          reserve_daily=reserve_daily)


def demo_settings():
    if os.environ.get("DEMO_STREAM_ENABLED", "false") != "true":
        return None
    if not os.environ.get("WORKER_QUEUE_URL") or os.environ.get("BRAND_SCHEDULER_ENABLED") == "true":
        raise ValueError("Demo yêu cầu SQS và tắt lịch nhãn hàng thông thường")
    brand_id = UUID(os.environ["DEMO_BRAND_ID"])
    session_id = UUID(os.environ["DEMO_SESSION_ID"])
    maximum = int(os.environ["DEMO_MAX_BATCHES"])
    expires = datetime.fromisoformat(os.environ["DEMO_EXPIRES_AT"].replace("Z", "+00:00"))
    if not 1 <= maximum <= 20 or expires.tzinfo is None:
        raise ValueError("Giới hạn demo không hợp lệ")
    return brand_id, session_id, maximum, expires


def provider_for_run(db_engine, run_id):
    with Session(db_engine) as db:
        run = db.get(TrackingRun, run_id)
        if run is None:
            raise ValueError("Không tìm thấy phiên")
        marker = run.config_snapshot.get("demo_session")
        batch_number = run.config_snapshot.get("demo_batch")
        brand_id = run.brand_id
    settings = demo_settings()
    if marker is not None:
        if settings is None or brand_id != settings[0] or marker != str(settings[1]) or type(batch_number) is not int or not 1 <= batch_number <= settings[2]:
            raise ValueError("Phiên demo không được phép xử lý")
        from app.demo_stream import DemoProvider
        return DemoProvider(run_id.hex, 6, batch_number)
    if settings is not None and brand_id == settings[0]:
        raise ValueError("Nhãn hàng demo không được gọi provider thật")
    return provider()


def queue_run_status(db_engine, event_id, run_id):
    with Session(db_engine) as db:
        return db.scalar(select(TrackingRun.status).join(TrackingOutbox, TrackingOutbox.run_id == TrackingRun.id)
                         .where(TrackingOutbox.id == event_id, TrackingRun.id == run_id))


def run_sentiment_if_enabled(db_engine, run_id=None, context=None):
    """Phân loại tùy chọn không làm phiên tracking đã hoàn tất thất bại."""
    if os.environ.get("SENTIMENT_ENABLED", "false") != "true":
        return
    claim = None
    try:
        limit = int(os.environ.get("SENTIMENT_DAILY_CALL_LIMIT", "0"))
        max_calls = int(os.environ.get("SENTIMENT_MAX_CALLS_PER_RUN", "0"))
        model_id = os.environ.get("SENTIMENT_MODEL_ID", "")
        if not model_id or not 1 <= limit <= 10000 or not 1 <= max_calls <= 100:
            raise ValueError("Cấu hình phân loại không đầy đủ")
        if context is not None and context.get_remaining_time_in_millis() < 30000:
            raise RuntimeError("Không đủ thời gian phân loại")
        claim = claim_sentiment_work(db_engine, run_id=run_id)
        if claim is None:
            failed = count_failed_sentiment_work(db_engine)
            if failed:
                print(json.dumps({"event": "sentiment_work_failed", "count": failed, "alert": 1}))
            return None
        claimed_run, lease_token = claim
        import boto3
        from botocore.config import Config
        client = boto3.client("bedrock-runtime", config=Config(connect_timeout=3, read_timeout=20,
                                                               retries={"total_max_attempts": 1}))
        classifier = BedrockSentimentClassifier(client, model_id)
        def within_deadline(content):
            if context is not None and context.get_remaining_time_in_millis() < 30000:
                raise RuntimeError("Không đủ thời gian phân loại")
            return classifier(content)
        result = classify_run(db_engine, claimed_run, within_deadline, model_id, max_calls=max_calls, daily_limit=limit,
                              before_write=lambda db: check_sentiment_lease(db, claimed_run, lease_token))
        status = finish_sentiment_work(db_engine, claimed_run, lease_token, result)
        print(json.dumps({"event": "sentiment_run", **result, "work_status": status, "alert": int(status == "failed")}))
        return claimed_run
    except Exception:
        if claim is not None:
            try:
                finish_sentiment_work(db_engine, claim[0], claim[1], None)
            except Exception:
                pass
        print(json.dumps({"event": "sentiment_error", "alert": 1}))
        return None


def run_alerts_if_enabled(db_engine, run_id, context=None):
    """Đánh giá các cửa sổ UTC đã hoàn tất sau khi xử lý tracking."""
    if os.environ.get("ALERT_EVALUATION_ENABLED", "false") != "true":
        return
    try:
        if context is not None and context.get_remaining_time_in_millis() < 20000:
            raise RuntimeError("Không đủ thời gian đánh giá")
        with Session(db_engine) as db:
            run = db.get(TrackingRun, run_id)
            if run is None:
                raise LookupError("Không tìm thấy phiên")
            brand_id = run.brand_id
            kinds = db.scalars(select(AlertRule.content_type).where(AlertRule.brand_id == brand_id,
                               AlertRule.enabled.is_(True)).order_by(AlertRule.content_type)).all()
        end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        for kind in kinds:
            if context is not None and context.get_remaining_time_in_millis() < 20000:
                raise RuntimeError("Không đủ thời gian đánh giá")
            result = evaluate_alert_rule(db_engine, brand_id, kind, end)
            print(json.dumps({"event": "alert_evaluation", "status": result["status"], "reason": result["reason"], "alert": 0}))
    except Exception:
        print(json.dumps({"event": "alert_evaluation_error", "alert": 1}))


def handle_queue(db_engine, records, context=None):
    """SQS at-least-once: chưa nhận hoặc đang chạy được thử lại; phiên cuối không chạy lần hai."""
    failures = []
    for record in records:
        message_id = record.get("messageId")
        try:
            data = json.loads(record["body"])
            event_id, run_id = UUID(data["event_id"]), UUID(data["run_id"])
            status = queue_run_status(db_engine, event_id, run_id)
            if status is None:
                raise ValueError("Unknown outbox event")
            if status == "running":
                raise RunNotQueued("Run is already active")
            if status != "queued":
                continue
            result = run_queued(db_engine, run_id, provider_for_run(db_engine, run_id))
            print(json.dumps({"event": "tracking_run", "run_id": str(run_id), "status": result[1],
                              "alert": int(result[1] in {"failed", "partial"})}))
            if result[1] in {"success", "partial", "failed"}:
                run_sentiment_if_enabled(db_engine, run_id, context)
                run_alerts_if_enabled(db_engine, run_id, context)
        except RunNotQueued:
            # Một consumer khác có thể đã nhận phiên kể từ lần đọc đầu.
            if queue_run_status(db_engine, event_id, run_id) == "running":
                failures.append({"itemIdentifier": message_id})
        except Exception:
            failures.append({"itemIdentifier": message_id})
            print(json.dumps({"event": "queue_processing_error", "alert": 1}))
    return {"batchItemFailures": failures}


def handler(event, context):
    db_engine = engine()
    if isinstance(event, dict) and "Records" in event:
        return handle_queue(db_engine, event["Records"], context)
    stale_analyses = reconcile_stale_analyses(db_engine)
    if stale_analyses:
        print(json.dumps({"event": "analysis_timeout", "count": stale_analyses, "alert": 1}))
    requeue_stale = os.environ.get("WORKER_REQUEUE_STALE", "false") == "true"
    stale_count = mark_stale(db_engine, 30, requeue=requeue_stale)
    if stale_count:
        print(json.dumps({"event": "tracking_timeout", "count": stale_count, "alert": 1}))
    settings = demo_settings()
    if os.environ.get("BRAND_SCHEDULER_ENABLED") == "true":
        enqueue_due(db_engine)
    if settings is not None:
        from app.demo_scheduler import enqueue_demo
        demo_run = enqueue_demo(db_engine, *settings)
        if demo_run is not None:
            print(json.dumps({"event": "demo_queued", "run_id": str(demo_run)}))
    queue_url = os.environ.get("WORKER_QUEUE_URL", "")
    if queue_url:
        import boto3
        published, failed = publish_pending(db_engine, boto3.client("sqs"), queue_url)
        if failed:
            print(json.dumps({"event": "outbox_publish_error", "count": failed, "alert": 1}))
        exhausted = count_exhausted(db_engine)
        if exhausted:
            print(json.dumps({"event": "outbox_publish_exhausted", "count": exhausted, "alert": 1}))
        classified = run_sentiment_if_enabled(db_engine, context=context)
        if classified is not None:
            run_alerts_if_enabled(db_engine, classified, context)
        return {"status": "dispatched", "published": published, "failed": failed}
    result = work_once(db_engine, provider)
    if result is None:
        classified = run_sentiment_if_enabled(db_engine, context=context)
        if classified is not None:
            run_alerts_if_enabled(db_engine, classified, context)
        return {"status": "idle"}
    print(json.dumps({"event": "tracking_run", "status": result[1],
                      "alert": int(result[1] in {"failed", "partial"})}))
    if result[1] in {"success", "partial", "failed"}:
        run_sentiment_if_enabled(db_engine, result[0], context)
        run_alerts_if_enabled(db_engine, result[0], context)
    return {"run_id": str(result[0]), "status": result[1]}

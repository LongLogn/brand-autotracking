"""Worker Lambda xử lý tối đa một phiên đã xếp trong mỗi lần gọi."""
import json
import os
from functools import partial
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.firecrawl import FirecrawlTikTok, reserve_daily_credits
from app.models import TrackingOutbox, TrackingRun
from app.outbox import count_exhausted, publish_pending
from app.tracking import RunNotQueued, mark_stale, run_queued
from app.scheduler import enqueue_due
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


def queue_run_status(db_engine, event_id, run_id):
    with Session(db_engine) as db:
        return db.scalar(select(TrackingRun.status).join(TrackingOutbox, TrackingOutbox.run_id == TrackingRun.id)
                         .where(TrackingOutbox.id == event_id, TrackingRun.id == run_id))


def handle_queue(db_engine, records):
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
            result = run_queued(db_engine, run_id, provider())
            print(json.dumps({"event": "tracking_run", "status": result[1],
                              "alert": int(result[1] in {"failed", "partial"})}))
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
        return handle_queue(db_engine, event["Records"])
    requeue_stale = os.environ.get("WORKER_REQUEUE_STALE", "false") == "true"
    stale_count = mark_stale(db_engine, 30, requeue=requeue_stale)
    if stale_count:
        print(json.dumps({"event": "tracking_timeout", "count": stale_count, "alert": 1}))
    if os.environ.get("BRAND_SCHEDULER_ENABLED") == "true":
        enqueue_due(db_engine)
    queue_url = os.environ.get("WORKER_QUEUE_URL", "")
    if queue_url:
        import boto3
        published, failed = publish_pending(db_engine, boto3.client("sqs"), queue_url)
        if failed:
            print(json.dumps({"event": "outbox_publish_error", "count": failed, "alert": 1}))
        exhausted = count_exhausted(db_engine)
        if exhausted:
            print(json.dumps({"event": "outbox_publish_exhausted", "count": exhausted, "alert": 1}))
        return {"status": "dispatched", "published": published, "failed": failed}
    result = work_once(db_engine, provider)
    if result is None:
        return {"status": "idle"}
    print(json.dumps({"event": "tracking_run", "status": result[1],
                      "alert": int(result[1] in {"failed", "partial"})}))
    return {"run_id": str(result[0]), "status": result[1]}

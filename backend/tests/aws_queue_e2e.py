"""Kiểm thử SQS/lịch AWS trên stack tạm cố định; chỉ chạy khi được bật rõ ràng."""
import json
import os
import time

import boto3

if os.getenv("TEST_ONLY_QUEUE_AWS") != "1":
    raise RuntimeError("Chỉ chạy trên stack AWS thử nghiệm riêng")

REGION = "ap-southeast-1"
STACK = "brand-queue-check-api-20261123"
FIXTURE = "brand-queue-check-fixture-20261123"
session = boto3.Session(region_name=REGION)
cf, lambdas, events, sqs, logs = (session.client(name) for name in ("cloudformation", "lambda", "events", "sqs", "logs"))
stack = cf.describe_stacks(StackName=STACK)["Stacks"][0]
if stack["StackStatus"] != "CREATE_COMPLETE":
    raise RuntimeError("Stack thử chưa sẵn sàng")
outputs = {row["OutputKey"]: row["OutputValue"] for row in stack["Outputs"]}
rule, worker, queue = outputs["WorkerRuleName"], outputs["WorkerFunctionName"], outputs["WorkerQueueUrl"]
if not rule.startswith(STACK) or not worker.startswith(STACK) or STACK not in queue:
    raise RuntimeError("Tài nguyên không thuộc stack thử")
group = f"/aws/lambda/{worker}"


def fixture(action, **kwargs):
    response = lambdas.invoke(FunctionName=FIXTURE, Payload=json.dumps({"action": action, **kwargs}).encode())
    body = json.loads(response["Payload"].read())
    if response.get("FunctionError"):
        raise RuntimeError(f"Fixture lỗi: {body.get('errorType', 'unknown')}")
    return body


def wait_for(label, predicate, seconds=240):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(5)
    raise RuntimeError(f"Quá thời gian chờ {label}")


def starts_after(ms):
    pages = logs.get_paginator("filter_log_events").paginate(logGroupName=group, startTime=ms,
                                                              filterPattern='"START RequestId"')
    return [event for page in pages for event in page.get("events", [])]


def check():
    brand = os.getenv("TEST_QUEUE_FIXTURE_BRAND") or fixture("create")["brand_id"]
    snapshot = lambda: fixture("inspect", brand_id=brand)
    events.enable_rule(Name=rule)

    def scheduled():
        result = snapshot()
        runs = [r for r in result["runs"] if r["scheduled"] and r["status"] in {"success", "partial", "failed"}]
        return (result, runs[0]) if runs else None

    first, run = wait_for("phiên theo lịch qua SQS", scheduled)
    if run["status"] != "success" or not run["published"] or run["attempts"] != 1:
        raise RuntimeError("Phiên theo lịch chưa thành công hoặc chưa phát outbox")
    print("Lịch → outbox → SQS → worker thành công", flush=True)

    events.disable_rule(Name=rule)
    time.sleep(10)
    before = snapshot()
    # Đồng hồ máy thử có thể nhanh hơn CloudWatch vài giây.
    start_ms = int((time.time() - 5) * 1000)
    sqs.send_message(QueueUrl=queue, MessageBody=json.dumps({"event_id": run["event_id"], "run_id": run["id"]}))
    wait_for("consumer nhận thông điệp lặp", lambda: starts_after(start_ms), seconds=120)
    time.sleep(5)
    after = snapshot()
    if before != after:
        raise RuntimeError("Thông điệp lặp làm thay đổi phiên hoặc dự phòng credit")
    print("Thông điệp SQS lặp không chạy lại phiên hoặc dự phòng credit", flush=True)

    expired = fixture("expire", brand_id=brand)["expired_run_id"]
    events.enable_rule(Name=rule)

    def recovered():
        result = snapshot()
        old = next((r for r in result["runs"] if r["id"] == expired), None)
        new = next((r for r in result["runs"] if r["recovered_from"] == expired and r["status"] in {"success", "partial", "failed"}), None)
        return (result, old, new) if old and new else None

    state, old, new = wait_for("phục hồi lease hết hạn", recovered)
    if old["status"] != "failed" or old["error"] != "worker_timeout" or new["status"] != "success" or not new["published"]:
        raise RuntimeError("Phục hồi lease chưa hoàn tất thành công")
    print("Lease hết hạn giả lập được đánh dấu lỗi và phục hồi qua SQS", flush=True)

    events.disable_rule(Name=rule)
    fixture("pause", brand_id=brand)
    before = snapshot()
    time.sleep(10)
    start_ms = int((time.time() - 5) * 1000)
    events.enable_rule(Name=rule)
    wait_for("lần quét lịch khi tạm dừng", lambda: starts_after(start_ms), seconds=120)
    time.sleep(5)
    events.disable_rule(Name=rule)
    if before != snapshot():
        raise RuntimeError("Lịch đã tạm dừng vẫn tạo phiên hoặc gọi provider")
    print("Nhãn hàng tạm dừng không tạo phiên mới", flush=True)


try:
    check()
finally:
    events.disable_rule(Name=rule)

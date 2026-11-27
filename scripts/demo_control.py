"""Bật hoặc dừng demo hữu hạn trên CloudFormation và database demo riêng."""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import ClientError


def stack_details(client, name):
    if not name.startswith("brand-demo-"):
        raise ValueError("Chỉ dùng stack API riêng có tên bắt đầu brand-demo-")
    stack = client.describe_stacks(StackName=name)["Stacks"][0]
    if stack["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"}:
        raise ValueError("Stack chưa sẵn sàng")
    params = {x["ParameterKey"]: x["ParameterValue"] for x in stack["Parameters"]}
    if not params.get("DatabaseHost", "").startswith("brand-demo-") or not params["DatabaseHost"].endswith(".rds.amazonaws.com"):
        raise ValueError("Database không phải môi trường demo riêng")
    return stack, params


def update(client, name, changes):
    stack, params = stack_details(client, name)
    if not set(changes) <= set(params):
        raise ValueError("Template stack không hỗ trợ chế độ demo")
    arguments = [{"ParameterKey": key, **({"ParameterValue": str(changes[key])}
                 if key in changes else {"UsePreviousValue": True})} for key in params]
    try:
        client.update_stack(StackName=name, UsePreviousTemplate=True, Parameters=arguments, Capabilities=["CAPABILITY_IAM"])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Message") == "No updates are to be performed.":
            return
        raise
    print("Đang chờ CloudFormation cập nhật...", flush=True)
    client.get_waiter("stack_update_complete").wait(StackName=name, WaiterConfig={"Delay": 10, "MaxAttempts": 90})


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "release", "stop"),
                        help="start: bật dòng dữ liệu (mốc rồi đợt tiêu cực); release: bắn đợt tích cực; stop: tắt lịch")
    parser.add_argument("--stack", required=True)
    parser.add_argument("--profile", default="profile-name-logn")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--brand-id", type=UUID)
    parser.add_argument("--session-id", type=UUID)
    parser.add_argument("--batches", type=int, choices=range(1, 21), default=3, help="Tổng số đợt, gồm đợt bắn bằng release")
    parser.add_argument("--auto-batches", type=int, choices=range(1, 21), default=2, help="Số đợt lịch tự xếp")
    parser.add_argument("--minutes", type=int, choices=range(5, 61), default=45)
    parser.add_argument("--interval-minutes", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    aws = boto3.Session(profile_name=args.profile, region_name=args.region)
    cf = aws.client("cloudformation")
    stack, params = stack_details(cf, args.stack)
    if args.action == "stop":
        update(cf, args.stack, {"WorkerScheduleState": "DISABLED"})
        print("Đã yêu cầu tắt lịch và mapping. Kiểm tra worker, SQS/DLQ và tài nguyên tính phí.")
        return
    if args.action == "release":
        if params.get("DemoStreamEnabled") != "true" or params.get("WorkerScheduleState") != "ENABLED":
            raise ValueError("Chưa bật dòng dữ liệu demo; chạy start trước")
        outputs = {x["OutputKey"]: x["OutputValue"] for x in stack.get("Outputs", [])}
        response = aws.client("lambda").invoke(FunctionName=outputs["WorkerFunctionName"],
                                               Payload=json.dumps({"demo_action": "release_next"}).encode())
        if response.get("FunctionError"):
            raise RuntimeError("Worker từ chối yêu cầu; xem log CloudWatch")
        print("Đã yêu cầu đợt tiếp theo. Nếu các đợt tự động chưa xong hoặc đã đủ số đợt, log ghi demo_release_skipped.")
        return
    if args.brand_id is None:
        parser.error("start cần --brand-id")
    if args.auto_batches > args.batches:
        parser.error("--auto-batches không được lớn hơn --batches")
    if params.get("WorkerScheduleState") != "DISABLED":
        raise ValueError("Dừng lịch trước khi chuẩn bị phiên demo mới")
    session_id = args.session_id or uuid4()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=args.minutes)).isoformat()
    print(f"Phiên demo: {session_id}; hết hạn: {expires}", flush=True)
    # Bật cấu hình và lịch trong một lần cập nhật; lần thu thập mốc chạy ở nhịp EventBridge kế tiếp.
    update(cf, args.stack, {"WorkerEnabled": "true", "WorkerQueueEnabled": "true", "WorkerScheduleState": "ENABLED",
                           "BrandSchedulerEnabled": "false", "DemoStreamEnabled": "true",
                           "DemoBrandId": args.brand_id, "DemoSessionId": session_id,
                           "DemoMaxBatches": args.batches, "DemoAutoBatches": args.auto_batches,
                           "DemoIntervalMinutes": args.interval_minutes, "DemoExpiresAt": expires})
    print(f"Đã bật dòng dữ liệu demo: {args.auto_batches} đợt tự động cách nhau khoảng {args.interval_minutes} phút; "
          "dùng release để bắn đợt tiếp theo. Lịch không tự tắt tài nguyên AWS.")


if __name__ == "__main__":
    main()

"""Cấu hình bảo vệ biên giữa frontend và backend."""
import os
from typing import Literal
from urllib.parse import urlsplit

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def cors_origins(value: str) -> list[str]:
    result = []
    for origin in (part.strip() for part in value.split(",")):
        if not origin:
            continue
        try:
            parsed = urlsplit(origin)
            host, port = parsed.hostname, parsed.port
        except ValueError:
            raise ValueError("CORS_ORIGINS không hợp lệ") from None
        is_local = host in {"localhost", "127.0.0.1", "::1"}
        if (not host or "*" in origin or parsed.username or parsed.password or parsed.path
                or parsed.query or parsed.fragment or port == 0
                or not (parsed.scheme == "https" or (parsed.scheme == "http" and is_local))):
            raise ValueError("CORS_ORIGINS không hợp lệ")
        result.append(origin)
    return list(dict.fromkeys(result))


def manual_worker_status() -> Literal["ready", "stopped", "unknown"]:
    """Đọc công tắc của stack vận hành. Lịch từng nhãn hàng dùng công tắc riêng."""
    stack_id = os.getenv("TRACKING_WORKER_STACK")
    if not stack_id:
        return "unknown"
    import boto3

    try:
        client = boto3.client("cloudformation", config=Config(connect_timeout=1, read_timeout=2,
                                                               retries={"total_max_attempts": 1}))
        stacks = client.describe_stacks(StackName=stack_id).get("Stacks", [])
    except (BotoCoreError, ClientError):
        return "unknown"
    if len(stacks) != 1 or stacks[0].get("StackStatus") not in {
        "CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"
    }:
        return "unknown"
    params = {item["ParameterKey"]: item.get("ParameterValue") for item in stacks[0].get("Parameters", [])}
    if params.get("WorkerEnabled") == "false" or params.get("WorkerScheduleState") == "DISABLED":
        return "stopped"
    if params.get("WorkerEnabled") == "true" and params.get("WorkerScheduleState") == "ENABLED":
        return "ready"
    return "unknown"

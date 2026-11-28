"""Tiến trình nền xử lý hàng đợi phân tích AI trong mỗi tiến trình API (EC2).

Khi hết lượt Bedrock trong phút, yêu cầu ở trạng thái `queued`; vòng lặp này thử lại
vài giây một lần, nên yêu cầu chạy ngay khi phút mới mở lượt. Nhiều tiến trình/máy cùng chạy
an toàn nhờ `FOR UPDATE SKIP LOCKED`. Lỗi được ghi log ngắn, không chứa nội dung nguồn.
"""
import json
import os
import random
import threading
import time

_started = False
_lock = threading.Lock()


def _loop(poll_seconds: float):
    from app.analysis import process_due_analyses, reconcile_stale_analyses
    from app.database import engine
    from app.main import analysis_provider
    model_id = os.environ.get("ANALYSIS_MODEL_ID", "")
    daily_limit = int(os.environ.get("BEDROCK_DAILY_CALL_LIMIT", "0"))
    last_reconcile = 0.0
    while True:
        time.sleep(poll_seconds + random.uniform(0, 1))
        try:
            if time.monotonic() - last_reconcile > 30:
                reconcile_stale_analyses(engine())
                last_reconcile = time.monotonic()
            processed = process_due_analyses(engine(), daily_limit=daily_limit,
                                             provider_factory=lambda: analysis_provider(model_id))
            if processed:
                print(json.dumps({"event": "analysis_queue_processed", "count": processed}), flush=True)
        except Exception as exc:
            print(json.dumps({"event": "analysis_queue_error", "error_type": type(exc).__name__}), flush=True)


def start_background_worker() -> bool:
    """Khởi động một luồng nền cho mỗi tiến trình nếu phân tích AI được bật."""
    global _started
    if (os.environ.get("ANALYSIS_ENABLED", "false") != "true" or os.environ.get("ANALYSIS_QUEUE_WORKER", "true") != "true"
            or not os.environ.get("ANALYSIS_MODEL_ID") or not 1 <= int(os.environ.get("BEDROCK_DAILY_CALL_LIMIT", "0")) <= 10000):
        return False
    with _lock:
        if _started:
            return False
        _started = True
    poll = float(os.environ.get("ANALYSIS_QUEUE_POLL_SECONDS", "3"))
    threading.Thread(target=_loop, args=(poll,), name="analysis-queue", daemon=True).start()
    return True

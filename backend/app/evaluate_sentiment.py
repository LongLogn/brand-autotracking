"""Đánh giá phân loại bằng tập có nhãn; mặc định không gọi model.

Ví dụ: python -m app.evaluate_sentiment --model-id ... --execute --max-calls 30 --daily-call-limit 30
Chỉ gửi dữ liệu được phép; báo cáo không in văn bản đầu vào.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import time

from app.models import SENTIMENT_ALGORITHM_VERSION
from app.sentiment import BedrockSentimentClassifier, SentimentBudgetExhausted, SentimentRateLimited, reserve_daily_call

DEFAULT_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sentiment_vietnamese_holdout.json"
REFERENCE_LABELS = {"positive", "negative", "neutral", "unknown"}


def load_cases(path: Path):
    raw = path.read_bytes()
    cases = json.loads(raw)
    if not isinstance(cases, list) or not 1 <= len(cases) <= 500:
        raise ValueError("Tập đánh giá không hợp lệ")
    seen = set()
    for row in cases:
        if (not isinstance(row, dict) or set(row) != {"id", "text", "label"} or
                not isinstance(row["id"], str) or not row["id"] or len(row["id"]) > 40 or row["id"] in seen or
                not isinstance(row["text"], str) or not row["text"].strip() or len(row["text"]) > 6000 or
                not isinstance(row["label"], str) or row["label"] not in REFERENCE_LABELS):
            raise ValueError("Mẫu đánh giá không hợp lệ")
        seen.add(row["id"])
    return cases, sha256(raw).hexdigest()


def evaluate_cases(cases, classifier, reserve, max_calls, *, interval_seconds=0, sleep=time.sleep):
    """Tính đúng, nhầm, không xác định và lỗi; không ghi lại nội dung."""
    if type(max_calls) is not int or not 0 <= max_calls <= 100:
        raise ValueError("Hạn mức đánh giá không hợp lệ")
    if not isinstance(interval_seconds, (int, float)) or isinstance(interval_seconds, bool) or not 0 <= interval_seconds <= 30:
        raise ValueError("Khoảng cách giữa các lời gọi không hợp lệ")
    results = []
    stopped = False
    stop_reason = None
    for row in cases[:max_calls]:
        if results and interval_seconds:
            sleep(interval_seconds)
        try:
            reserve()
        except SentimentRateLimited:
            stopped = True
            stop_reason = "rate_limit"
            break
        except SentimentBudgetExhausted:
            stopped = True
            stop_reason = "daily_limit"
            break
        try:
            predicted = classifier(row["text"])
            if predicted not in REFERENCE_LABELS:
                predicted = "error"
        except Exception:
            predicted = "error"
        results.append({"id": row["id"], "expected": row["label"], "predicted": predicted})
    confusion = Counter((row["expected"], row["predicted"]) for row in results)
    return {"evaluated": len(results), "matched": sum(row["expected"] == row["predicted"] for row in results),
            "unknown": sum(row["predicted"] == "unknown" for row in results),
            "errors": sum(row["predicted"] == "error" for row in results),
            "not_evaluated": len(cases) - len(results), "budget_exhausted": stopped, "stop_reason": stop_reason,
            "confusion": [{"expected": expected, "predicted": predicted, "count": count}
                          for (expected, predicted), count in sorted(confusion.items())], "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--max-calls", type=int, default=0)
    parser.add_argument("--daily-call-limit", type=int, default=0)
    parser.add_argument("--interval-seconds", type=float, default=6, help="Khoảng nghỉ giữa các lời gọi, tối đa 30 giây")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, help="Tệp kết quả mới; không ghi đè tệp đã tồn tại")
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Tệp kết quả đã tồn tại")
    cases, fingerprint = load_cases(args.fixture)
    report = {"model_id": args.model_id, "classifier_version": SENTIMENT_ALGORITHM_VERSION,
              "fixture_sha256": fingerprint, "fixture_count": len(cases), "executed": args.execute}
    if not args.execute:
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            with args.output.open("x", encoding="utf-8") as output:
                output.write(text + "\n")
        print(text); return
    if not 1 <= args.max_calls <= min(len(cases), 100) or not 1 <= args.daily_call_limit <= 10000 or not 0 <= args.interval_seconds <= 30:
        parser.error("Cần hạn mức lượt gọi dương và không vượt kích thước tập")
    import boto3
    from botocore.config import Config
    from app.database import engine
    db_engine = engine()
    client = boto3.client("bedrock-runtime", config=Config(connect_timeout=3, read_timeout=25,
                                                           retries={"total_max_attempts": 1}))
    class Meter:
        input_tokens = output_tokens = calls = 0
        def __init__(self):
            self.errors = Counter()
        def converse(self, **kwargs):
            try:
                response = client.converse(**kwargs)
            except Exception as exc:
                code = getattr(exc, "response", {}).get("Error", {}).get("Code", "Other")
                allowed = {"ThrottlingException", "ServiceUnavailableException", "ModelTimeoutException",
                           "AccessDeniedException", "ValidationException", "ModelNotReadyException"}
                self.errors[code if code in allowed else "Other"] += 1
                raise
            usage = response.get("usage", {})
            self.calls += 1
            self.input_tokens += usage.get("inputTokens", 0)
            self.output_tokens += usage.get("outputTokens", 0)
            return response
    meter = Meter()
    try:
        report.update(evaluate_cases(cases, BedrockSentimentClassifier(meter, args.model_id),
                                     lambda: reserve_daily_call(db_engine, args.daily_call_limit), args.max_calls,
                                     interval_seconds=args.interval_seconds))
        report["usage"] = {"successful_responses": meter.calls, "input_tokens": meter.input_tokens, "output_tokens": meter.output_tokens}
        report["provider_errors"] = dict(meter.errors)
        report["interval_seconds"] = args.interval_seconds
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            with args.output.open("x", encoding="utf-8") as output:
                output.write(text + "\n")
        print(text)
    finally:
        db_engine.dispose()


if __name__ == "__main__":
    main()

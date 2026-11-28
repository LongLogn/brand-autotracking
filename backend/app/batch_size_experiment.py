"""Thử nghiệm chọn cỡ lô phân loại cảm xúc với Bedrock thật.

Đầu vào: JSON danh sách {"c": nội dung, "l": nhãn chuẩn} (nhãn do phân loại từng câu).
Chạy: python -m app.batch_size_experiment sample.json --sizes 1:40,10,20,30,50 --profile <sso>
In bảng: tỷ lệ khớp nhãn chuẩn, tỷ lệ bỏ sót, thời gian, token mỗi lượt. Không ghi database.
Giữ nhịp tối đa ~14 lượt/phút để không vượt quota 20 lượt/phút của tài khoản.
"""
import argparse
import json
import time

from app.sentiment import BedrockBatchSentimentClassifier, BedrockSentimentClassifier

MIN_GAP_SECONDS = 4.3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sample")
    parser.add_argument("--sizes", default="1:40,10,20,30,50", help="cỡ[:số mẫu], phân tách bằng dấu phẩy")
    parser.add_argument("--model", default="apac.amazon.nova-lite-v1:0")
    parser.add_argument("--profile")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--out")
    args = parser.parse_args()
    import boto3
    from botocore.config import Config
    client = boto3.Session(profile_name=args.profile, region_name=args.region).client(
        "bedrock-runtime", config=Config(read_timeout=60, retries={"total_max_attempts": 1}))
    items = json.load(open(args.sample, encoding="utf-8"))
    items = [row for row in items if row["c"].strip()]
    last_call = [0.0]

    def paced(fn, *call_args):
        wait = MIN_GAP_SECONDS - (time.monotonic() - last_call[0])
        if wait > 0:
            time.sleep(wait)
        last_call[0] = time.monotonic()
        start = time.monotonic()
        try:
            return fn(*call_args), time.monotonic() - start, None
        except Exception as exc:
            return None, time.monotonic() - start, type(exc).__name__

    report = []
    for spec in args.sizes.split(","):
        size, _, limit = spec.partition(":")
        size = int(size)
        rows = items[:int(limit)] if limit else items
        agree = missing = calls = errors = 0
        latencies, tokens_in, tokens_out = [], 0, 0
        if size == 1:
            single = BedrockSentimentClassifier(client, args.model)
            for row in rows:
                label, seconds, error = paced(single, row["c"])
                calls += 1
                latencies.append(seconds)
                if error:
                    errors += 1; missing += 1
                elif label == row["l"]:
                    agree += 1
        else:
            batch = BedrockBatchSentimentClassifier(client, args.model)
            for offset in range(0, len(rows), size):
                chunk = rows[offset:offset + size]
                labels, seconds, error = paced(batch, [row["c"] for row in chunk])
                calls += 1
                latencies.append(seconds)
                usage = batch.last_usage or {}
                tokens_in += usage.get("inputTokens", 0); tokens_out += usage.get("outputTokens", 0)
                if error:
                    errors += 1; missing += len(chunk)
                    continue
                for row, label in zip(chunk, labels):
                    if label is None:
                        missing += 1
                    elif label == row["l"]:
                        agree += 1
        result = {"size": size, "items": len(rows), "calls": calls, "errors": errors,
                  "agreement": round(agree / len(rows), 3), "missing": round(missing / len(rows), 3),
                  "avg_latency_s": round(sum(latencies) / len(latencies), 2), "max_latency_s": round(max(latencies), 2),
                  "avg_tokens_in": round(tokens_in / calls) if size > 1 else None,
                  "avg_tokens_out": round(tokens_out / calls) if size > 1 else None,
                  "items_per_minute_at_17_calls": 17 * size}
        report.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.out:
        json.dump(report, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

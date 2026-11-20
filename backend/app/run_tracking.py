"""Chạy thử một phiên cục bộ; không in nội dung nguồn hoặc khóa."""
import argparse
from functools import partial
import os
from uuid import UUID

from app.database import engine
from app.firecrawl import FirecrawlTikTok, reserve_daily_credits
from app.tracking import run_once, run_queued


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--brand-id", type=UUID)
    target.add_argument("--run-id", type=UUID)
    parser.add_argument("--max-calls", required=True, type=int, choices=range(1, 11), metavar="1..10")
    parser.add_argument("--daily-estimated-credit-budget", required=True, type=int,
                        choices=range(0, 1000001), metavar="0..1000000")
    parser.add_argument("--estimated-credits-per-call", type=int, choices=range(1, 1001), default=2, metavar="1..1000")
    args = parser.parse_args()
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        parser.error("Thiếu FIRECRAWL_API_KEY")
    db_engine = engine()
    provider = FirecrawlTikTok(key, max_calls=args.max_calls, estimated_credits_per_call=args.estimated_credits_per_call,
                               reserve_daily=partial(reserve_daily_credits, db_engine, args.daily_estimated_credit_budget))
    run_id, status = (run_once(db_engine, args.brand_id, provider) if args.brand_id
                      else run_queued(db_engine, args.run_id, provider))
    print(f"run_id={run_id} status={status} remaining_calls={provider.remaining}")


if __name__ == "__main__":
    main()

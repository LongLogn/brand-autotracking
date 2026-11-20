"""Worker cục bộ thử nghiệm, mỗi phiên có giới hạn số lần gọi Firecrawl."""
import argparse
from functools import partial
import os
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.firecrawl import FirecrawlTikTok, reserve_daily_credits
from app.models import TrackingRun
from app.tracking import RunNotActive, RunNotQueued, mark_stale, run_queued


def work_once(db_engine, provider_factory):
    with Session(db_engine) as db:
        run_id = db.scalar(select(TrackingRun.id).where(TrackingRun.status == "queued")
                           .order_by(TrackingRun.queued_at, TrackingRun.id).limit(1))
    if run_id is None:
        return None
    try:
        return run_queued(db_engine, run_id, provider_factory())
    except (RunNotQueued, RunNotActive):
        # Worker khác đã nhận phiên sau khi ta đọc hàng đợi.
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-calls", required=True, type=int, choices=range(1, 11), metavar="1..10")
    parser.add_argument("--poll-seconds", type=int, choices=range(1, 61), default=5, metavar="1..60")
    parser.add_argument("--max-attempts", type=int, choices=range(1, 4), default=1, metavar="1..3",
                        help="Số lần thử tối đa cho lỗi tạm thời; mỗi lần tính vào max-calls")
    parser.add_argument("--search-pages", type=int, choices=range(1, 4), default=1, metavar="1..3")
    parser.add_argument("--comment-pages", type=int, choices=range(1, 4), default=1, metavar="1..3")
    parser.add_argument("--estimated-credit-budget", type=int, choices=range(0, 10001), metavar="0..10000")
    parser.add_argument("--estimated-credits-per-call", type=int, choices=range(1, 1001), default=2, metavar="1..1000")
    parser.add_argument("--daily-estimated-credit-budget", type=int, choices=range(0, 1000001), required=True,
                        metavar="0..1000000", help="Dự phòng credit chung mỗi ngày UTC qua database")
    parser.add_argument("--once", action="store_true", help="Chỉ thử nhận một phiên rồi thoát")
    parser.add_argument("--stale-after-minutes", type=int, choices=range(30, 1441), metavar="30..1440",
                        help="Tùy chọn đánh dấu lỗi phiên chạy quá thời hạn; không tự chạy lại")
    args = parser.parse_args()
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        parser.error("Thiếu FIRECRAWL_API_KEY")
    db_engine = engine()
    reserve_daily = partial(reserve_daily_credits, db_engine, args.daily_estimated_credit_budget)
    factory = lambda: FirecrawlTikTok(key, max_calls=args.max_calls, max_attempts=args.max_attempts,
                                     search_pages=args.search_pages, comment_pages=args.comment_pages,
                                     estimated_credit_budget=args.estimated_credit_budget,
                                     estimated_credits_per_call=args.estimated_credits_per_call,
                                     reserve_daily=reserve_daily)
    while True:
        if args.stale_after_minutes is not None:
            mark_stale(db_engine, args.stale_after_minutes)
        result = work_once(db_engine, factory)
        if result:
            # ASCII giúp worker không dừng khi stdout của Windows không hỗ trợ UTF-8.
            print(f"run_id={result[0]} status={result[1]}", flush=True)
        if args.once:
            break
        if result is None:
            time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()

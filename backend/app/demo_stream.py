"""Phát dữ liệu giả có giới hạn vào một nhãn hàng trong database demo cục bộ."""
import argparse
import os
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.adapters.tiktok import ranked_posts
from app.tracking import run_once


class DemoProvider:
    """Mỗi đợt là một bài giả và các bình luận giả, không gọi mạng."""

    attempt_source = "demo"

    def __init__(self, batch_id, count, batch_number=1):
        self.batch_id = batch_id
        self.count = count
        self.batch_number = batch_number
        self.created = int(datetime.now(timezone.utc).timestamp())

    def search(self, keyword):
        return [{"aweme_id": f"demo-{self.batch_id}",
                 "url": f"https://www.tiktok.com/@demo/video/{self.batch_id}",
                 "desc": "[DỮ LIỆU GIẢ] Mây Tea ra mắt sản phẩm mới.",
                 "create_time": self.created,
                 "statistics": {"digg_count": 5, "comment_count": self.count}}]

    def comments(self, url):
        phrases = (("Mình thích sản phẩm này.", "Hương vị thơm ngon.", "Đồ uống quá ngọt.")
                   if self.batch_number == 1 else
                   ("Đồ uống quá ngọt.", "Giao hàng chậm.", "Mình thích sản phẩm này."))
        return [{"cid": f"demo-{self.batch_id}-{i}",
                 "text": f"[DỮ LIỆU GIẢ] {phrases[i % len(phrases)]}",
                 "create_time": self.created, "digg_count": i % 4}
                for i in range(self.count)]

    def normalize_posts(self, posts):
        rows = ranked_posts(posts)
        for row in rows:
            row["source"] = "demo"
            row["url"] = f"https://example.invalid/demo/{self.batch_id}"
        return rows


def demo_url(value):
    if not value:
        raise ValueError("Cần DEMO_DATABASE_URL cho database demo cục bộ")
    url = make_url(value)
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database != "brand_demo" or url.query):
        raise ValueError("Chỉ cho phép PostgreSQL localhost, database brand_demo")
    return url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand-id", type=UUID, required=True)
    parser.add_argument("--batches", type=int, choices=range(1, 21), default=3)
    parser.add_argument("--interval", type=int, choices=range(1, 301), default=10)
    parser.add_argument("--comments", type=int, choices=range(1, 31), default=6)
    args = parser.parse_args()
    try:
        url = demo_url(os.environ.get("DEMO_DATABASE_URL"))
    except ValueError as exc:
        parser.error(str(exc))
    engine = create_engine(url)
    try:
        for batch in range(args.batches):
            batch_id = uuid4().hex
            run_id, status = run_once(engine, args.brand_id, DemoProvider(batch_id, args.comments, batch + 1))
            print(f"demo_batch={batch + 1} run_id={run_id} status={status}", flush=True)
            if status != "success":
                raise RuntimeError("Phiên giả lập không thành công; đã dừng")
            if batch + 1 < args.batches:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Demo stopped", flush=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

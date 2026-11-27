"""Phát dữ liệu giả có giới hạn vào một nhãn hàng trong database demo cục bộ."""
import argparse
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.adapters.tiktok import ranked_posts
from app.tracking import run_once


DEMO_PREFIX = "[DỮ LIỆU GIẢ] "

# Câu mẫu theo nhãn; nhãn giả lập được gán theo đúng câu, không do mô hình suy luận.
DEMO_PHRASES = {
    "positive": ("Gà rán giòn rụm, ngon tuyệt.", "Burger bò phô mai rất đáng tiền.", "Combo gà rán kèm Coca mát lạnh.",
                 "Nhân viên phục vụ nhiệt tình.", "Sẽ quay lại KFCC lần nữa.", "Gà sốt cay vừa miệng."),
    "neutral": ("Mới thấy quảng cáo KFCC.", "Combo gà rán giá bao nhiêu nhỉ?",
                "Chi nhánh KFCC gần nhất ở đâu vậy?", "Hôm nay mới ăn thử lần đầu."),
    "negative": ("Gà rán bị khô, kém giòn.", "Giao hàng chậm quá.", "Burger nguội, bánh bị mềm.",
                 "Đợi giao hơn một tiếng.", "Coca hết ga khi giao tới.", "Giá cao mà phần ăn ít."),
}
PHRASE_LABELS = {phrase: label for label, phrases in DEMO_PHRASES.items() for phrase in phrases}

# Kịch bản: mốc 20/100, đợt tiêu cực đưa lũy kế lên 60/200, đợt tích cực xuống 65/300.
DEMO_SCENARIO = {
    1: {"positive": 60, "neutral": 20, "negative": 20},
    2: {"positive": 40, "neutral": 20, "negative": 40},
    3: {"positive": 80, "neutral": 15, "negative": 5},
}
DEMO_POST_TEXT = {
    1: "KFCC ra mắt combo gà rán mới.",
    2: "Khách hàng phản ánh về chất lượng gà rán KFCC.",
    3: "KFCC cải thiện chất lượng gà rán và giao hàng.",
}


def demo_label(text):
    """Nhãn giả lập của một bình luận demo; None nếu không phải câu mẫu."""
    if not isinstance(text, str) or not text.startswith(DEMO_PREFIX):
        return None
    body = text[len(DEMO_PREFIX):].split(" (mẫu ", 1)[0]
    return PHRASE_LABELS.get(body)


def scenario_comments(batch_number):
    plan = DEMO_SCENARIO.get(batch_number, DEMO_SCENARIO[3])
    rows = []
    for label in ("negative", "positive", "neutral"):
        phrases = DEMO_PHRASES[label]
        rows.extend((label, phrases[i % len(phrases)]) for i in range(plan[label]))
    # Trộn ổn định để danh sách không tách theo nhãn.
    return [rows[(i * 37) % len(rows)] for i in range(len(rows))] if len(rows) % 37 else rows


class DemoProvider:
    """Mỗi đợt là một bài giả và các bình luận giả, không gọi mạng.

    Khi không truyền count, số bình luận và tỷ lệ theo DEMO_SCENARIO của đợt.
    """

    attempt_source = "demo"

    def __init__(self, batch_id, count=None, batch_number=1):
        self.batch_id = batch_id
        self.count = count
        self.batch_number = batch_number
        self.created = int(datetime.now(timezone.utc).timestamp())

    def _rows(self):
        if self.count is None:
            return [phrase for _, phrase in scenario_comments(self.batch_number)]
        phrases = (("Gà rán giòn rụm, ngon tuyệt.", "Burger bò phô mai rất đáng tiền.", "Gà rán bị khô, kém giòn.")
                   if self.batch_number == 1 else
                   ("Gà rán bị khô, kém giòn.", "Giao hàng chậm quá.", "Gà rán giòn rụm, ngon tuyệt."))
        return [phrases[i % len(phrases)] for i in range(self.count)]

    def search(self, keyword):
        text = DEMO_POST_TEXT.get(self.batch_number, DEMO_POST_TEXT[1])
        return [{"aweme_id": f"demo-{self.batch_id}",
                 "url": f"https://www.tiktok.com/@demo/video/{self.batch_id}",
                 "desc": f"{DEMO_PREFIX}{text}",
                 "create_time": self.created,
                 "statistics": {"digg_count": 5, "comment_count": len(self._rows())}}]

    def comments(self, url):
        rows = self._rows()
        suffix = self.count is None
        return [{"cid": f"demo-{self.batch_id}-{i}",
                 "text": f"{DEMO_PREFIX}{phrase}" + (f" (mẫu {self.batch_number}.{i + 1})" if suffix else ""),
                 "create_time": self.created, "digg_count": i % 4}
                for i, phrase in enumerate(rows)]

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


def run_scenario(engine, brand_id, batches, interval, session_id=None):
    """Chạy kịch bản qua lịch demo, worker, nhãn giả lập và cảnh báo như trên AWS (không gửi email).

    Truyền lại session_id để chạy tiếp các đợt sau của cùng phiên demo.
    """
    from sqlalchemy.orm import Session
    from app.demo_alerts import process_demo_run
    from app.demo_scheduler import enqueue_demo
    from app.models import TrackingRun
    from app.tracking import run_queued

    resumed = session_id is not None
    session_id = session_id or uuid4()
    expires = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)
    for index in range(batches):
        # Đợt đầu như lịch tự động; các đợt sau như người vận hành bắn release, không chờ khoảng cách phút.
        run_id = enqueue_demo(engine, brand_id, session_id, 20, expires, interval_minutes=1, auto_batches=1,
                              manual=resumed or index > 0)
        if run_id is None:
            raise RuntimeError("Không xếp được đợt demo; kiểm tra cấu hình nhãn hàng hoặc phiên đang chạy")
        with Session(engine) as db:
            batch = db.get(TrackingRun, run_id).config_snapshot["demo_batch"]
        _, status = run_queued(engine, run_id, DemoProvider(run_id.hex, None, batch))
        result = process_demo_run(engine, run_id) if status == "success" else {"status": status}
        print(f"demo_batch={batch} run_id={run_id} status={status} alert={result['status']}", flush=True)
        if status != "success":
            raise RuntimeError("Phiên giả lập không thành công; đã dừng")
        if index + 1 < batches:
            time.sleep(interval)
    return session_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand-id", type=UUID, required=True)
    parser.add_argument("--batches", type=int, choices=range(1, 21), default=3)
    parser.add_argument("--interval", type=int, choices=range(1, 301), default=10)
    parser.add_argument("--comments", type=int, choices=range(1, 31), default=6)
    parser.add_argument("--scenario", action="store_true", help="Dùng kịch bản mốc/tiêu cực/tích cực và cảnh báo theo lần thu thập")
    parser.add_argument("--session-id", type=UUID, help="Với --scenario: chạy tiếp đợt sau của phiên demo đã có")
    args = parser.parse_args()
    try:
        url = demo_url(os.environ.get("DEMO_DATABASE_URL"))
    except ValueError as exc:
        parser.error(str(exc))
    engine = create_engine(url)
    if args.scenario:
        try:
            session_id = run_scenario(engine, args.brand_id, args.batches, args.interval, args.session_id)
            print(f"demo_session={session_id}", flush=True)
        finally:
            engine.dispose()
        return
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

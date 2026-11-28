"""Chuẩn hóa tập con từ provider TikTok của Firecrawl, không lưu hồ sơ người dùng."""
from datetime import datetime, timezone
from urllib.parse import urlsplit


def count(value):
    return value if type(value) is int and value >= 0 else None


def timestamp(value):
    if type(value) is not int or value < 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def post_record(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("url"), str):
        return None
    url = raw["url"]
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != "https" or parts.username or parts.password or port not in (None, 443) or (host != "tiktok.com" and not host.endswith(".tiktok.com")):
        return None
    source_id = raw.get("aweme_id")
    source_id = source_id if isinstance(source_id, str) and source_id.strip() else None
    stats = raw.get("statistics") if isinstance(raw.get("statistics"), dict) else {}
    return {"source": "tiktok", "source_id": source_id, "url": url,
            "content": raw.get("desc") if isinstance(raw.get("desc"), str) else None,
            "posted_at": timestamp(raw.get("create_time")), "likes": count(stats.get("digg_count")),
            "views": count(stats.get("play_count")), "comment_count": count(stats.get("comment_count")),
            "shares": count(stats.get("share_count")), "maybe_duplicate": source_id is None}


def comment_record(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("text"), str) or not raw["text"].strip():
        return None
    source_id = raw.get("cid")
    source_id = source_id if isinstance(source_id, str) and source_id.strip() else None
    return {"source_id": source_id, "content": raw["text"], "posted_at": timestamp(raw.get("create_time")),
            "likes": count(raw.get("digg_count")), "maybe_duplicate": source_id is None}


def ranked_posts(items, posted_after=None):
    """Giữ thứ tự TikTok trả về (từ trên xuống), loại ID trùng; không gộp bài thiếu ID.

    Khi có posted_after, bỏ bài cũ hơn mốc này hoặc không rõ thời điểm đăng.
    """
    rows = [post_record(item) for item in items]
    rows = [row for row in rows if row is not None]
    if posted_after is not None:
        rows = [row for row in rows if row["posted_at"] is not None
                and datetime.fromisoformat(row["posted_at"]) >= posted_after]
    seen = set()
    result = []
    for row in rows:
        source_id = row["source_id"]
        if source_id is not None and source_id in seen:
            continue
        if source_id is not None:
            seen.add(source_id)
        result.append(row)
    return result

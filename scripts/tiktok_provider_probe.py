"""Thử Firecrawl Alexandria: tìm video và kiểm tra bình luận của video đứng đầu."""
import argparse
import json
import os
import sys
from pathlib import Path

from firecrawl_probe import post

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.adapters.tiktok import comment_record, ranked_posts


def provider_call(capability, options, key):
    result = post("scrape", {"alexandria": {"provider": "scrapecreators",
                   "capability": capability, "options": options}}, key)
    records = (result.get("data") or {}).get("alexandria") or []
    if not result.get("success") or not records or records[0].get("error"):
        raise RuntimeError("Provider thất bại hoặc cần điều kiện truy cập; kiểm tra Firecrawl dashboard.")
    payload = records[0].get("data") or {}
    if not payload.get("success"):
        raise RuntimeError("Provider không trả kết quả thành công.")
    return payload


def rank_posts(items):
    """Chỉ xếp bài có lượt thích là số nguyên; không biến thiếu thành 0."""
    return [{"url": row["url"], "likes": row["likes"], "posted_at": row["posted_at"]}
            for row in ranked_posts(items) if row["likes"] is not None]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        print("Thiếu FIRECRAWL_API_KEY", file=sys.stderr)
        return 2
    try:
        found = provider_call("tiktok/search-videos", {"query": args.query, "sort_by": "most-liked", "trim": True}, key)
        items = found.get("search_item_list") or []
        ranked = rank_posts(items)
        print(json.dumps({"search_count": len(items), "ranked_count": len(ranked),
                          "search_cursor": found.get("cursor"), "top": ranked[:3]}, ensure_ascii=False, indent=2))
        if not ranked:
            print("Không có kết quả có URL và lượt thích hợp lệ.")
            return 1
        comments = provider_call("tiktok/video-comments", {"url": ranked[0]["url"], "trim": False}, key)
        rows = comments.get("comments") or []
        normalized = [row for item in rows if (row := comment_record(item)) is not None]
        print(json.dumps({"comments_returned": len(rows), "comments_total_reported": comments.get("total"),
                          "comments_cursor": comments.get("cursor"),
                          "normalized_comments": len(normalized),
                          "with_likes": sum(row["likes"] is not None for row in normalized),
                          "with_comment_id": sum(row["source_id"] is not None for row in normalized)}, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, ValueError, TypeError) as exc:
        print(f"Không hoàn thành phép thử: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

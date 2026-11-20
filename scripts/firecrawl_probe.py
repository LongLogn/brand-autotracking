"""Thử Search → Scrape Firecrawl; không tự động lưu nội dung trang."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.firecrawl.dev/v2/"


class DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(request.full_url, code, "redirect denied", headers, fp)


def tiktok_metrics(markdown):
    """Đọc bảng chỉ số kiểu đã quan sát; thiếu hoặc đổi định dạng là không khả dụng."""
    match = re.search(
        r"(?im)^\|\s*Views\s*\|\s*Likes\s*\|\s*Comments\s*\|\s*Shares\s*\|\s*Saves\s*\|\s*$"
        r"\s*\n\|[\s:|\-]+\|\s*\n\|([^\n]+)\|", markdown,
    )
    if not match:
        return None
    values = [value.strip().replace(",", "") for value in match.group(1).split("|")]
    if len(values) != 5 or not all(value.isascii() and value.isdigit() for value in values):
        return None
    return dict(zip(("views", "likes", "comments", "shares", "saves"), map(int, values)))


def post(endpoint, payload, key):
    request = urllib.request.Request(
        BASE + endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.build_opener(DenyRedirect()).open(request, timeout=90) as response:
            body = response.read(10 * 1024 * 1024 + 1)
            if len(body) > 10 * 1024 * 1024:
                raise RuntimeError(f"Firecrawl {endpoint}: phản hồi vượt giới hạn")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise RuntimeError(f"Firecrawl {endpoint}: HTTP {code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Firecrawl {endpoint}: lỗi kết nối hoặc phản hồi không hợp lệ ({type(exc).__name__})") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Truy vấn Search, có thể dùng site:")
    parser.add_argument("--index", type=int, default=1, help="Vị trí kết quả web cần scrape, từ 1 đến 5")
    args = parser.parse_args()
    if not 1 <= args.index <= 5:
        parser.error("--index phải từ 1 đến 5")
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        print("Thiếu biến môi trường FIRECRAWL_API_KEY.", file=sys.stderr)
        return 2
    try:
        search = post("search", {"query": args.query, "limit": 5, "sources": [{"type": "web"}]}, key)
        if not search.get("success"):
            raise RuntimeError("Search thất bại; kiểm tra quyền và credit trong Firecrawl.")
        results = search.get("data", {}).get("web", [])
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', '(không có tiêu đề)')} — {result.get('url', '')}")
        if len(results) < args.index or not results[args.index - 1].get("url"):
            raise RuntimeError("Không có URL tại vị trí được chọn.")
        url = results[args.index - 1]["url"]
        scrape = post("scrape", {"url": url, "formats": ["markdown"], "maxAge": 0}, key)
        if not scrape.get("success"):
            raise RuntimeError("Scrape thất bại; kiểm tra trạng thái trên Firecrawl.")
        data = scrape.get("data") or {}
        metadata = data.get("metadata") or {}
        markdown = data.get("markdown") or ""
        hostname = (urllib.parse.urlsplit(url).hostname or "").lower()
        print(json.dumps({"url": url, "http_status": metadata.get("statusCode"),
                          "markdown_characters": len(markdown),
                          "tiktok_metrics_candidate": tiktok_metrics(markdown) if hostname == "tiktok.com" or hostname.endswith(".tiktok.com") else None,
                          "credits_scrape": metadata.get("creditsUsed"),
                          "credits_search": search.get("creditsUsed")}, ensure_ascii=False, indent=2))
        print("Nội dung không được lưu; số ký tự không xác nhận có bài viết hoặc bình luận.")
        return 0 if markdown else 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Client Firecrawl có giới hạn; không ghi log response hoặc khóa."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from sqlalchemy import Date, cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FirecrawlCreditReservation


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class DenyRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Không chuyển bearer key tới URL đích của redirect.
        raise HTTPError(request.full_url, code, "redirect denied", headers, fp)


def reserve_daily_credits(db_engine, daily_limit, amount):
    """Dự phòng nguyên tử trước lời gọi, không hoàn lại khi lỗi hoặc không chắc phí."""
    if not 0 <= daily_limit <= 1000000 or not 1 <= amount <= 1000:
        raise ValueError("Giới hạn credit dự phòng không hợp lệ")
    if amount > daily_limit:
        raise ProviderError("daily_estimated_credit_limit")
    table = FirecrawlCreditReservation.__table__
    with Session(db_engine) as db, db.begin():
        day = db.scalar(select(cast(func.timezone("UTC", func.now()), Date)))
        statement = insert(table).values(day=day, daily_limit=daily_limit, unit_estimate=amount, reserved=amount)
        statement = statement.on_conflict_do_update(
            index_elements=[table.c.day],
            set_={"reserved": table.c.reserved + amount},
            where=(table.c.daily_limit == daily_limit) & (table.c.unit_estimate == amount)
                  & (table.c.reserved + amount <= table.c.daily_limit),
        ).returning(table.c.day)
        if db.scalar(statement) is None:
            raise ProviderError("daily_estimated_credit_limit")


class FirecrawlTikTok:
    def __init__(self, api_key: str, max_calls: int = 5, max_attempts: int = 1,
                 search_pages: int = 1, comment_pages: int = 1,
                 estimated_credit_budget: int | None = None, estimated_credits_per_call: int = 2,
                 reserve_daily=None, before_request=None):
        if (not api_key or not 1 <= max_calls <= 10 or not 1 <= max_attempts <= 3
                or not 1 <= search_pages <= 3 or not 1 <= comment_pages <= 3
                or not 1 <= estimated_credits_per_call <= 1000
                or (estimated_credit_budget is not None and not 0 <= estimated_credit_budget <= 10000)):
            raise ValueError("Cần API key, 1–10 lần gọi, 1–3 lần thử và 1–3 trang")
        self._key = api_key
        self.remaining = max_calls
        self.max_attempts = max_attempts
        self.search_pages, self.comment_pages = search_pages, comment_pages
        self.estimated_credits_remaining = estimated_credit_budget
        self.estimated_credits_per_call = estimated_credits_per_call
        self.reserve_daily = reserve_daily
        self.before_request = before_request

    def _call(self, capability, options):
        for attempt in range(self.max_attempts):
            try:
                return self._request(capability, options)
            except ProviderError as exc:
                transient = exc.code in {"network_or_invalid_response", "http_429", "http_500", "http_502", "http_503", "http_504"}
                if not transient or attempt + 1 >= self.max_attempts or self.remaining <= 0:
                    raise
                time.sleep(min(2 ** attempt, 2))

    def _request(self, capability, options):
        if self.remaining <= 0:
            raise ProviderError("call_limit")
        if self.estimated_credits_remaining is not None:
            if self.estimated_credits_remaining < self.estimated_credits_per_call:
                raise ProviderError("estimated_credit_limit")
        if self.before_request is not None:
            self.before_request()
        if self.reserve_daily is not None:
            self.reserve_daily(self.estimated_credits_per_call)
        if self.estimated_credits_remaining is not None:
            self.estimated_credits_remaining -= self.estimated_credits_per_call
        self.remaining -= 1
        payload = json.dumps({"alexandria": {"provider": "scrapecreators", "capability": capability,
                                             "options": options}}).encode("utf-8")
        request = Request("https://api.firecrawl.dev/v2/scrape", data=payload, method="POST", headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + self._key,
            "x-request-id": str(uuid4()),
        })
        try:
            with build_opener(DenyRedirect()).open(request, timeout=90) as response:
                body = response.read(10 * 1024 * 1024 + 1)
                if len(body) > 10 * 1024 * 1024:
                    raise ProviderError("response_too_large")
                result = json.loads(body)
        except HTTPError as exc:
            code = exc.code
            exc.close()
            raise ProviderError(f"http_{code}") from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError):
            raise ProviderError("network_or_invalid_response") from None
        if not isinstance(result, dict) or not result.get("success"):
            raise ProviderError("provider_error")
        data = result.get("data")
        items = data.get("alexandria") if isinstance(data, dict) else None
        if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict) or items[0].get("error"):
            raise ProviderError("provider_error")
        output = items[0].get("data")
        if not isinstance(output, dict) or output.get("success") is not True:
            raise ProviderError("provider_error")
        return output

    def search(self, keyword):
        return self._pages("tiktok/search-videos", {"query": keyword, "sort_by": "most-liked", "trim": True},
                           "search_item_list", self.search_pages, "invalid_search_response")

    def comments(self, url):
        return self._pages("tiktok/video-comments", {"url": url, "trim": False},
                           "comments", self.comment_pages, "invalid_comments_response")

    def _pages(self, capability, options, field, limit, error):
        records, seen = [], set()
        for page in range(limit):
            data = self._call(capability, options)
            items = data.get(field)
            if not isinstance(items, list):
                raise ProviderError(error)
            records.extend(items)
            cursor = data.get("cursor")
            if not items or type(cursor) is not int or cursor <= 0 or cursor in seen:
                break
            seen.add(cursor)
            options = {**options, "cursor": cursor}
        return records

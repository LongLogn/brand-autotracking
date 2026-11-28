import io
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from app.firecrawl import DenyRedirect, FirecrawlTikTok, ProviderError, date_posted


class FirecrawlTests(unittest.TestCase):
    def test_estimated_credit_budget_reserves_before_each_request(self):
        body = {"success": True, "data": {"alexandria": [{"data": {"success": True, "search_item_list": []}}]}}
        opener = Mock(); opener.open.side_effect = [io.BytesIO(json.dumps(body).encode())]
        with patch("app.firecrawl.build_opener", return_value=opener):
            client = FirecrawlTikTok("secret", max_calls=5, estimated_credit_budget=3, estimated_credits_per_call=2)
            self.assertEqual(client.search("brand"), [])
            with self.assertRaises(ProviderError) as error:
                client.search("brand")
            self.assertEqual(error.exception.code, "estimated_credit_limit")
            self.assertEqual(client.remaining, 4)
            self.assertEqual(opener.open.call_count, 1)

    def test_daily_budget_rejects_before_network_and_reserves_retries(self):
        reserve = Mock(side_effect=ProviderError("daily_estimated_credit_limit"))
        opener = Mock()
        with patch("app.firecrawl.build_opener", return_value=opener):
            with self.assertRaises(ProviderError) as error:
                FirecrawlTikTok("secret", reserve_daily=reserve).search("brand")
        self.assertEqual(error.exception.code, "daily_estimated_credit_limit")
        reserve.assert_called_once_with(2)
        opener.open.assert_not_called()
        reserve = Mock()
        opener.open.side_effect = URLError("network")
        with patch("app.firecrawl.build_opener", return_value=opener), patch("app.firecrawl.time.sleep"):
            with self.assertRaises(ProviderError):
                FirecrawlTikTok("secret", max_calls=2, max_attempts=2, reserve_daily=reserve).search("brand")
        self.assertEqual(reserve.call_count, 2)

    def test_before_request_guard_runs_for_each_retry_and_can_block_network(self):
        opener = Mock(); opener.open.side_effect = URLError("unavailable")
        guard = Mock()
        with patch("app.firecrawl.build_opener", return_value=opener), patch("app.firecrawl.time.sleep"):
            with self.assertRaises(ProviderError):
                FirecrawlTikTok("secret", max_calls=2, max_attempts=2, before_request=guard).search("brand")
        self.assertEqual(guard.call_count, 2)
        guard = Mock(side_effect=RuntimeError("lease expired"))
        opener.reset_mock()
        with patch("app.firecrawl.build_opener", return_value=opener):
            with self.assertRaisesRegex(RuntimeError, "lease expired"):
                FirecrawlTikTok("secret", before_request=guard).search("brand")
        opener.open.assert_not_called()

    def test_pagination_uses_cursor_and_stops_on_repeated_cursor(self):
        def response(ids, cursor):
            return io.BytesIO(json.dumps({"success": True, "data": {"alexandria": [{"data": {
                "success": True, "comments": [{"cid": value} for value in ids], "cursor": cursor}}]}}).encode())
        opener = Mock()
        opener.open.side_effect = [response(["1"], 20), response(["2"], 20)]
        with patch("app.firecrawl.build_opener", return_value=opener):
            client = FirecrawlTikTok("secret", max_calls=3, comment_pages=3)
            self.assertEqual(client.comments("https://www.tiktok.com/@a/video/1"), [{"cid": "1"}, {"cid": "2"}])
        self.assertEqual(opener.open.call_count, 2)
        first = json.loads(opener.open.call_args_list[0].args[0].data)
        second = json.loads(opener.open.call_args_list[1].args[0].data)
        self.assertNotIn("cursor", first["alexandria"]["options"])
        self.assertEqual(second["alexandria"]["options"]["cursor"], 20)

    def test_pagination_never_exceeds_call_budget(self):
        body = {"success": True, "data": {"alexandria": [{"data": {"success": True,
                "comments": [{"cid": "1"}], "cursor": 20}}]}}
        opener = Mock(); opener.open.return_value = io.BytesIO(json.dumps(body).encode())
        with patch("app.firecrawl.build_opener", return_value=opener):
            with self.assertRaises(ProviderError) as error:
                FirecrawlTikTok("secret", max_calls=1, comment_pages=2).comments("https://www.tiktok.com/@a/video/1")
        self.assertEqual(error.exception.code, "call_limit")
        self.assertEqual(opener.open.call_count, 1)

    def test_retry_transient_errors_consumes_call_budget(self):
        body = {"success": True, "data": {"alexandria": [{"data": {"success": True, "search_item_list": []}}]}}
        opener = Mock()
        opener.open.side_effect = [URLError("unavailable"), io.BytesIO(json.dumps(body).encode())]
        with patch("app.firecrawl.build_opener", return_value=opener), patch("app.firecrawl.time.sleep") as sleep:
            client = FirecrawlTikTok("secret", max_calls=2, max_attempts=2)
            self.assertEqual(client.search("brand"), [])
            self.assertEqual(client.remaining, 0)
            self.assertEqual(opener.open.call_count, 2)
            sleep.assert_called_once_with(1)
            with self.assertRaises(ProviderError) as error:
                client.search("brand")
            self.assertEqual(error.exception.code, "call_limit")

    def test_retry_stops_at_budget_and_ignores_permanent_errors(self):
        opener = Mock()
        opener.open.side_effect = URLError("unavailable")
        with patch("app.firecrawl.build_opener", return_value=opener), patch("app.firecrawl.time.sleep") as sleep:
            with self.assertRaises(ProviderError) as error:
                FirecrawlTikTok("secret", max_calls=1, max_attempts=3).search("brand")
            self.assertEqual(error.exception.code, "network_or_invalid_response")
            self.assertEqual(opener.open.call_count, 1)
            sleep.assert_not_called()
        opener.open.reset_mock()
        opener.open.side_effect = HTTPError("https://api.firecrawl.dev", 401, "unauthorized", {}, None)
        with patch("app.firecrawl.build_opener", return_value=opener), patch("app.firecrawl.time.sleep") as sleep:
            with self.assertRaises(ProviderError) as error:
                FirecrawlTikTok("secret", max_calls=3, max_attempts=3).search("brand")
            self.assertEqual(error.exception.code, "http_401")
            self.assertEqual(opener.open.call_count, 1)
            sleep.assert_not_called()

    def test_budget_and_response_shape(self):
        body = {"success": True, "data": {"alexandria": [{"data": {"success": True, "search_item_list": []}}]}}
        opener = Mock(); opener.open.return_value = io.BytesIO(json.dumps(body).encode())
        with patch("app.firecrawl.build_opener", return_value=opener):
            client = FirecrawlTikTok("secret", max_calls=1)
            self.assertEqual(client.search("brand"), [])
            with self.assertRaises(ProviderError) as result:
                client.comments("https://www.tiktok.com/@a/video/1")
            self.assertEqual(result.exception.code, "call_limit")
            self.assertEqual(opener.open.call_count, 1)

    def test_search_uses_tiktok_order_and_lookback_window(self):
        body = {"success": True, "data": {"alexandria": [{"data": {"success": True, "search_item_list": []}}]}}
        opener = Mock(); opener.open.side_effect = lambda *a, **k: io.BytesIO(json.dumps(body).encode())
        with patch("app.firecrawl.build_opener", return_value=opener):
            client = FirecrawlTikTok("secret", max_calls=5)
            client.search("brand")
            client.lookback_days = 90
            client.search("brand")
            client.lookback_days = 365
            client.search("brand")
        options = [json.loads(call.args[0].data)["alexandria"]["options"] for call in opener.open.call_args_list]
        self.assertEqual([o["sort_by"] for o in options], ["relevance"] * 3)
        self.assertEqual([o.get("date_posted") for o in options], [None, "last-3-months", "all-time"])
        self.assertEqual([date_posted(d) for d in (1, 2, 7, 8, 30, 31, 180, 181)],
                         ["yesterday", "this-week", "this-week", "this-month", "this-month",
                          "last-3-months", "last-6-months", "all-time"])

    def test_provider_error_is_not_empty_success(self):
        body = {"success": True, "data": {"alexandria": [{"error": {"message": "secret or private"}}]}}
        opener = Mock(); opener.open.return_value = io.BytesIO(json.dumps(body).encode())
        with patch("app.firecrawl.build_opener", return_value=opener):
            with self.assertRaises(ProviderError) as result:
                FirecrawlTikTok("secret").search("brand")
            self.assertEqual(str(result.exception), "provider_error")

    def test_redirect_is_refused_and_response_is_bounded(self):
        request = Request("https://api.firecrawl.dev/v2/scrape", headers={"Authorization": "Bearer secret"})
        with self.assertRaises(HTTPError) as redirect:
            DenyRedirect().redirect_request(request, None, 302, "redirect", {}, "https://example.test")
        redirect.exception.close()
        opener = Mock(); opener.open.return_value = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
        with patch("app.firecrawl.build_opener", return_value=opener):
            with self.assertRaises(ProviderError) as result:
                FirecrawlTikTok("secret").search("brand")
        self.assertEqual(result.exception.code, "response_too_large")


if __name__ == "__main__":
    unittest.main()

"""Kiểm thử độc lập, không kết nối mạng hoặc sử dụng dữ liệu cá nhân."""
import unittest
import contextlib
import io
import os
import sys
from unittest.mock import patch

from tiktok_provider_probe import main, provider_call, rank_posts


class ProbeTests(unittest.TestCase):
    def test_rank_only_valid_likes_and_tiktok_hosts(self):
        items = [
            {"url": "https://www.tiktok.com/a", "statistics": {"digg_count": 3}},
            {"url": "https://www.tiktok.com/b", "statistics": {"digg_count": 9}},
            {"url": "https://www.tiktok.com/c", "statistics": {}},
            {"url": "https://tiktok.com.example/a", "statistics": {"digg_count": 100}},
            {"url": "https://tiktok.com/d", "statistics": {"digg_count": True}},
        ]
        self.assertEqual([row["likes"] for row in rank_posts(items)], [9, 3])

    def test_provider_failure_cannot_be_counted_as_empty_success(self):
        response = {"success": True, "data": {"alexandria": [{"error": {"code": "failed"}}]}}
        with patch("tiktok_provider_probe.post", return_value=response):
            with self.assertRaises(RuntimeError):
                provider_call("tiktok/search-videos", {}, "secret")

    def test_successful_empty_result(self):
        response = {"success": True, "data": {"alexandria": [{"data": {"success": True, "search_item_list": []}}]}}
        with patch("tiktok_provider_probe.post", return_value=response):
            self.assertEqual(provider_call("tiktok/search-videos", {}, "secret")["search_item_list"], [])

    def test_two_calls_choose_highest_likes_without_printing_comment_text(self):
        search = {"success": True, "data": {"alexandria": [{"data": {"success": True,
                  "search_item_list": [{"aweme_id": "1", "url": "https://tiktok.com/a", "statistics": {"digg_count": 1}},
                                       {"aweme_id": "2", "url": "https://tiktok.com/b", "statistics": {"digg_count": 9}}]}}]}}
        comments = {"success": True, "data": {"alexandria": [{"data": {"success": True,
                    "comments": [{"cid": "c1", "text": "private comment", "digg_count": 2}]}}]}}
        output = io.StringIO()
        with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "secret"}), patch.object(sys, "argv", ["probe", "--query", "test"]), \
                patch("tiktok_provider_probe.post", side_effect=[search, comments]) as request, contextlib.redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[1].args[1]["alexandria"]["options"]["url"], "https://tiktok.com/b")
        self.assertNotIn("private comment", output.getvalue())
        self.assertNotIn("secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()

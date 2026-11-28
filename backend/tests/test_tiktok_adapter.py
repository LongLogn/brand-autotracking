import unittest
from datetime import datetime, timezone

from app.adapters.tiktok import comment_record, post_record, ranked_posts


class TiktokAdapterTests(unittest.TestCase):
    def test_normalizes_without_personal_fields(self):
        raw = {"aweme_id": "10", "url": "https://www.tiktok.com/@test/video/10", "desc": "brand",
               "create_time": 0, "statistics": {"digg_count": 0, "comment_count": 3},
               "author": {"name": "not retained"}}
        result = post_record(raw)
        self.assertEqual(result["likes"], 0)
        self.assertIsNone(result["views"])
        self.assertEqual(result["posted_at"], "1970-01-01T00:00:00+00:00")
        self.assertNotIn("author", result)

    def test_keeps_provider_order_and_reject_foreign_host(self):
        rows = ranked_posts([
            {"url": "https://tiktok.com/a", "statistics": {}},
            {"url": "https://tiktok.com/b", "statistics": {"digg_count": 0}},
            {"url": "https://tiktok.com/c", "statistics": {"digg_count": 8}},
            {"url": "https://tiktok.com.attacker.test/", "statistics": {"digg_count": 99}},
        ])
        self.assertEqual([row["url"][-1] for row in rows], ["a", "b", "c"])

    def test_posted_after_drops_old_and_undated_posts(self):
        cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = ranked_posts([
            {"url": "https://tiktok.com/old", "create_time": int(cutoff.timestamp()) - 1},
            {"url": "https://tiktok.com/edge", "create_time": int(cutoff.timestamp())},
            {"url": "https://tiktok.com/undated"},
            {"url": "https://tiktok.com/new", "create_time": int(cutoff.timestamp()) + 3600},
        ], cutoff)
        self.assertEqual([row["url"] for row in rows], ["https://tiktok.com/edge", "https://tiktok.com/new"])
        self.assertEqual(len(ranked_posts([{"url": "https://tiktok.com/undated"}])), 1)

    def test_comment_id_and_invalid_values(self):
        row = comment_record({"cid": "123", "aweme_id": "video", "text": "hi", "digg_count": True,
                              "create_time": 99999999999999999999, "user": {"id": "private"}})
        self.assertEqual(row["source_id"], "123")
        self.assertIsNone(row["likes"])
        self.assertIsNone(row["posted_at"])
        self.assertNotIn("user", row)
        self.assertTrue(comment_record({"aweme_id": "video", "text": "hi"})["maybe_duplicate"])
        self.assertIsNone(comment_record({"text": " "}))

    def test_duplicate_ids_keep_first_unknown_ids_remain(self):
        rows = ranked_posts([
            {"aweme_id": "1", "url": "https://tiktok.com/a", "statistics": {"digg_count": 1}},
            {"aweme_id": "1", "url": "https://tiktok.com/b", "statistics": {"digg_count": 9}},
            {"url": "https://tiktok.com/c", "statistics": {}},
            {"url": "https://tiktok.com/d", "statistics": {}},
        ])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["likes"], 1)
        self.assertTrue(all(row["maybe_duplicate"] for row in rows[1:]))


if __name__ == "__main__":
    unittest.main()

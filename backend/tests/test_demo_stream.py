import unittest

from app.demo_stream import DemoProvider, demo_url
from app.adapters.tiktok import comment_record, post_record


class DemoStreamTests(unittest.TestCase):
    def test_provider_labels_and_normalizes_data(self):
        provider = DemoProvider("abc123", 6)
        post = provider.normalize_posts(provider.search("KFCC"))[0]
        comments = [comment_record(row) for row in provider.comments(post["url"])]
        self.assertIn("DỮ LIỆU GIẢ", post["content"])
        self.assertEqual(post["source"], "demo")
        self.assertTrue(post["url"].startswith("https://example.invalid/"))
        self.assertEqual(len({row["source_id"] for row in comments}), 6)
        self.assertTrue(all("DỮ LIỆU GIẢ" in row["content"] for row in comments))
        self.assertEqual(provider.search("khác")[0]["aweme_id"], "demo-abc123")
        first = provider.comments(post["url"])
        later = DemoProvider("def456", 6, 2).comments(post["url"])
        self.assertGreater(sum('ngon' in item['text'] or 'đáng tiền' in item['text'] for item in first),
                           sum('ngon' in item['text'] or 'đáng tiền' in item['text'] for item in later))

    def test_database_is_local_and_named_demo(self):
        self.assertEqual(demo_url("postgresql+psycopg://u:p@localhost/brand_demo").database, "brand_demo")
        for url in (None, "postgresql://u:p@example.com/brand_demo", "postgresql://u:p@localhost/brand_test", "postgresql://u:p@localhost/brand_demo?host=example.com", "sqlite:///brand_demo"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                demo_url(url)

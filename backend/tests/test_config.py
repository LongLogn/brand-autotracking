import unittest

from app.config import cors_origins


class CorsConfigTests(unittest.TestCase):
    def test_explicit_origins_and_empty(self):
        self.assertEqual(cors_origins(""), [])
        self.assertEqual(cors_origins("http://localhost:5173, https://app.example.test, http://localhost:5173"),
                         ["http://localhost:5173", "https://app.example.test"])

    def test_reject_unsafe_or_malformed_origin(self):
        for value in ("*", "https://*.example.test", "http://example.test", "https://user:pw@example.test",
                      "https://example.test/path", "https://example.test?token=abc", "https://example.test:bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cors_origins(value)

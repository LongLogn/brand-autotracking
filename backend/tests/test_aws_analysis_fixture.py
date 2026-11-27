"""Đảm bảo fixture AWS không ghi vào database ngoài môi trường thử."""
import os
import unittest
from unittest.mock import patch

from tests.aws_analysis_fixture import handler
from tests.aws_queue_fixture import handler as queue_handler


class AwsFixtureSafetyTests(unittest.TestCase):
    def test_rejects_missing_flag_or_wrong_database_before_connecting(self):
        for env in (
            {"TEST_ONLY_AWS_FIXTURE": "0", "DATABASE_HOST": "brand-ai-check-data-test.rds.amazonaws.com"},
            {"TEST_ONLY_AWS_FIXTURE": "1", "DATABASE_HOST": "production.rds.amazonaws.com"},
            {"TEST_ONLY_AWS_FIXTURE": "1", "DATABASE_HOST": "brand-ai-check-data-test.example.com"},
        ):
            with self.subTest(env=env), patch.dict(os.environ, env), patch("tests.aws_analysis_fixture.engine") as db:
                with self.assertRaises(RuntimeError):
                    handler({}, None)
                db.assert_not_called()

    def test_queue_fixture_rejects_other_databases_before_connecting(self):
        with patch.dict(os.environ, {"TEST_ONLY_AWS_FIXTURE": "1", "DATABASE_HOST": "production.rds.amazonaws.com"}), \
             patch("tests.aws_queue_fixture.engine") as db:
            with self.assertRaises(RuntimeError):
                queue_handler({}, None)
            db.assert_not_called()

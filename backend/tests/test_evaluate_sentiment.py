"""Kiểm thử giới hạn và cách tính kết quả đánh giá mô hình."""
import unittest

from app.evaluate_sentiment import DEFAULT_FIXTURE, evaluate_cases, load_cases
from app.sentiment import SentimentBudgetExhausted


class SentimentEvaluationTests(unittest.TestCase):
    def test_fixture_and_budget_are_bounded(self):
        cases, digest = load_cases(DEFAULT_FIXTURE)
        self.assertEqual((len(cases), len(digest)), (30, 64))
        calls = []
        def reserve():
            if len(calls) == 2:
                raise SentimentBudgetExhausted()
            calls.append(True)
        result = evaluate_cases(cases, lambda _: "positive", reserve, 30)
        self.assertEqual((result["evaluated"], result["not_evaluated"], result["budget_exhausted"]), (2, 28, True))
        self.assertTrue(all("text" not in item for item in result["results"]))

    def test_unknown_and_provider_errors_are_not_counted_as_matches(self):
        cases = [{"id": "a", "label": "negative", "text": "x"}, {"id": "b", "label": "neutral", "text": "y"}]
        outputs = iter(["unknown", RuntimeError("provider")])
        def classify(_):
            item = next(outputs)
            if isinstance(item, Exception):
                raise item
            return item
        result = evaluate_cases(cases, classify, lambda: None, 2)
        self.assertEqual((result["matched"], result["unknown"], result["errors"]), (0, 1, 1))

    def test_interval_occurs_between_calls_and_is_bounded(self):
        cases = [{"id": "a", "label": "negative", "text": "x"}, {"id": "b", "label": "neutral", "text": "y"}]
        waits = []
        evaluate_cases(cases, lambda _: "unknown", lambda: None, 2, interval_seconds=4, sleep=waits.append)
        self.assertEqual(waits, [4])
        with self.assertRaises(ValueError):
            evaluate_cases(cases, lambda _: "unknown", lambda: None, 2, interval_seconds=31)

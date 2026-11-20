import unittest
from decimal import Decimal

from app.alert_rules import evaluate_increase


class AlertRuleTests(unittest.TestCase):
    def evaluate(self, previous, current, **overrides):
        options = dict(growth_percent=Decimal("50"), minimum_current=5,
                       comparable=True, fully_classified=True)
        options.update(overrides)
        return evaluate_increase(previous, current, **options)

    def test_growth_threshold_and_minimum(self):
        self.assertEqual(self.evaluate(10, 15).status, "triggered")
        self.assertEqual(self.evaluate(10, 14).status, "not_triggered")
        self.assertEqual(self.evaluate(2, 3).status, "not_triggered")

    def test_zero_baseline_requires_absolute_rule(self):
        self.assertEqual(self.evaluate(0, 15).reason, "zero_baseline")
        self.assertEqual(self.evaluate(0, 15, absolute_threshold=15).status, "triggered")
        self.assertEqual(self.evaluate(0, 14, absolute_threshold=15).status, "not_triggered")

    def test_missing_or_uncomparable_data_fails_closed(self):
        for overrides in ({"comparable": False}, {"fully_classified": False}):
            self.assertEqual(self.evaluate(10, 15, **overrides).status, "insufficient_data")
        self.assertEqual(self.evaluate(None, 15).status, "insufficient_data")

    def test_reject_invalid_inputs(self):
        for previous in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                self.evaluate(previous, 15)
        with self.assertRaises(ValueError):
            self.evaluate(10, 15, growth_percent=Decimal("NaN"))
        for overrides in ({"minimum_current": True}, {"minimum_current": 1.5},
                          {"absolute_threshold": False}, {"growth_percent": 50}):
            with self.assertRaises(ValueError):
                self.evaluate(10, 15, **overrides)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

from botocore.exceptions import EndpointConnectionError

from app.config import cors_origins, manual_worker_status


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


class ManualWorkerTests(unittest.TestCase):
    def test_stack_state_separates_worker_from_brand_schedule(self):
        with patch.dict(os.environ, {"TRACKING_WORKER_STACK": "brand-demo-api"}), patch("boto3.client") as client:
            describe = client.return_value.describe_stacks
            params = {"WorkerEnabled": "true", "WorkerScheduleState": "DISABLED", "BrandSchedulerEnabled": "false"}
            stack = {"StackStatus": "UPDATE_COMPLETE"}
            describe.return_value = {"Stacks": [stack]}
            for schedule, expected in (("DISABLED", "stopped"), ("ENABLED", "ready")):
                params["WorkerScheduleState"] = schedule
                stack["Parameters"] = [{"ParameterKey": key, "ParameterValue": value} for key, value in params.items()]
                self.assertEqual(manual_worker_status(), expected)
            describe.assert_called_with(StackName="brand-demo-api")
            stack["StackStatus"] = "UPDATE_IN_PROGRESS"
            self.assertEqual(manual_worker_status(), "unknown")
            describe.side_effect = EndpointConnectionError(endpoint_url="https://example.test")
            self.assertEqual(manual_worker_status(), "unknown")

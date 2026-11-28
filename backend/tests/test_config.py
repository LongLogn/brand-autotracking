import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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


class DatabaseTlsTests(unittest.TestCase):
    def test_rds_url_verifies_certificate_and_hostname(self):
        from app.database import database_url
        with TemporaryDirectory() as tmp:
            ca = Path(tmp) / "ca.pem"
            ca.touch()
            values = {"DATABASE_HOST": "example.ap-southeast-1.rds.amazonaws.com", "DATABASE_NAME": "brand_tracking",
                      "DATABASE_SECRET_ARN": "qa-db", "DATABASE_SSL_ROOT_CERT": str(ca)}
            with patch.dict(os.environ, values, clear=True), patch("boto3.client") as client:
                client.return_value.get_secret_value.return_value = {"SecretString": '{"username":"fixture","password":"fixture"}'}
                url = database_url()
                self.assertEqual(url.host, values["DATABASE_HOST"])
                self.assertEqual(dict(url.query), {"sslmode": "verify-full", "sslrootcert": str(ca.resolve())})
                ca.unlink()
                with self.assertRaisesRegex(RuntimeError, "Thiếu CA bundle"):
                    database_url()

    def test_local_database_url_keeps_its_transport_configuration(self):
        from app.database import database_url
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://fixture@localhost/db"}, clear=True):
            url = database_url()
        self.assertEqual(url.host, "localhost")
        self.assertEqual(dict(url.query), {})

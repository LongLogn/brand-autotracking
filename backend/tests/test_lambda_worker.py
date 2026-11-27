"""Kiểm thử ranh giới worker Lambda mà không gọi AWS hoặc Firecrawl."""
import io
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app import lambda_worker


class LambdaWorkerTests(unittest.TestCase):
    def setUp(self):
        self.reconcile = patch.object(lambda_worker, "reconcile_stale_analyses", return_value=0)
        self.reconcile.start()

    def tearDown(self):
        self.reconcile.stop()

    def test_enabled_sentiment_uses_budget_and_isolates_provider_failure(self):
        run_id = uuid4()
        boto = SimpleNamespace(client=Mock(return_value="bedrock"))
        config = SimpleNamespace(Config=Mock(return_value="bounded-config"))
        env = {"SENTIMENT_ENABLED": "true", "SENTIMENT_MODEL_ID": "example-model",
               "SENTIMENT_DAILY_CALL_LIMIT": "3", "SENTIMENT_MAX_CALLS_PER_RUN": "2"}
        result = {"processed": 1, "failed": 0, "attempted": 1, "remaining": 0, "exhausted": False, "daily_limit_reached": False, "rate_limit_reached": False}
        lease = uuid4()
        with patch.dict(sys.modules, {"boto3": boto, "botocore": SimpleNamespace(), "botocore.config": config}), \
             patch.dict(os.environ, env), patch.object(lambda_worker, "BedrockSentimentClassifier") as factory, \
             patch.object(lambda_worker, "claim_sentiment_work", return_value=(run_id, lease)), \
             patch.object(lambda_worker, "finish_sentiment_work", return_value="complete") as finish, \
             patch.object(lambda_worker, "classify_run", return_value=result) as classify, \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            lambda_worker.run_sentiment_if_enabled("db", run_id)
            self.assertEqual(classify.call_args.args[:2], ("db", run_id))
            self.assertEqual(classify.call_args.kwargs["max_calls"], 2)
            self.assertEqual(classify.call_args.kwargs["daily_limit"], 3)
            self.assertTrue(callable(classify.call_args.kwargs["before_write"]))
            finish.assert_called_once_with("db", run_id, lease, result)
            self.assertEqual(json.loads(output.getvalue()), {"event": "sentiment_run", **result, "work_status": "complete", "alert": 0})
            factory.assert_called_once_with("bedrock", "example-model")
            self.assertEqual(config.Config.call_args.kwargs["retries"], {"total_max_attempts": 1})
        with patch.dict(os.environ, env), patch("sys.stdout", new_callable=io.StringIO) as output:
            lambda_worker.run_sentiment_if_enabled("db", run_id, SimpleNamespace(get_remaining_time_in_millis=lambda: 100))
            self.assertEqual(json.loads(output.getvalue()), {"event": "sentiment_error", "alert": 1})

    def test_sentiment_disabled_or_misconfigured_never_invokes_model(self):
        with patch.dict(os.environ, {"SENTIMENT_ENABLED": "false"}), \
             patch.object(lambda_worker, "classify_run") as classify:
            lambda_worker.run_sentiment_if_enabled("db", uuid4())
            classify.assert_not_called()
        with patch.dict(os.environ, {"SENTIMENT_ENABLED": "true", "SENTIMENT_MODEL_ID": "test", "SENTIMENT_DAILY_CALL_LIMIT": "0"}), \
             patch.object(lambda_worker, "classify_run") as classify, patch("sys.stdout", new_callable=io.StringIO) as output:
            lambda_worker.run_sentiment_if_enabled("db", uuid4())
            classify.assert_not_called()
            self.assertEqual(json.loads(output.getvalue()), {"event": "sentiment_error", "alert": 1})

    def test_scheduler_drains_backlog_even_without_new_tracking(self):
        run_id = uuid4()
        with patch.dict(os.environ, {"BRAND_SCHEDULER_ENABLED": "false", "WORKER_QUEUE_URL": ""}), \
             patch.object(lambda_worker, "engine", return_value="db"), \
             patch.object(lambda_worker, "mark_stale", return_value=0), \
             patch.object(lambda_worker, "work_once", return_value=None), \
             patch.object(lambda_worker, "run_sentiment_if_enabled", return_value=run_id) as sentiment, \
             patch.object(lambda_worker, "run_alerts_if_enabled") as alerts:
            self.assertEqual(lambda_worker.handler({}, None), {"status": "idle"})
            sentiment.assert_called_once_with("db", context=None)
            alerts.assert_called_once_with("db", run_id, None)

    def test_queue_runs_once_and_redelivery_after_success_is_acknowledged(self):
        event_id, run_id = uuid4(), uuid4()
        records = [{"messageId": "one", "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})}]
        with patch.object(lambda_worker, "queue_run_status", side_effect=["queued", "success"]), \
             patch.object(lambda_worker, "provider_for_run", return_value="provider"), \
             patch.object(lambda_worker, "run_queued", return_value=(run_id, "success")) as run, \
             patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(lambda_worker.handle_queue("db", records), {"batchItemFailures": []})
            self.assertEqual(lambda_worker.handle_queue("db", records), {"batchItemFailures": []})
        run.assert_called_once_with("db", run_id, "provider")

    def test_queue_retries_active_and_invalid_messages(self):
        event_id, run_id = uuid4(), uuid4()
        records = [{"messageId": "active", "body": json.dumps({"event_id": str(event_id), "run_id": str(run_id)})},
                   {"messageId": "invalid", "body": "not-json"}]
        with patch.object(lambda_worker, "queue_run_status", return_value="running"), \
             patch.object(lambda_worker, "provider") as provider, \
             patch("sys.stdout", new_callable=io.StringIO):
            result = lambda_worker.handle_queue("db", records)
        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "active"}, {"itemIdentifier": "invalid"}]})
        provider.assert_not_called()

    def test_scheduler_publishes_outbox_in_queue_mode(self):
        sqs = Mock()
        boto = SimpleNamespace(client=Mock(return_value=sqs))
        with patch.dict(sys.modules, {"boto3": boto}), \
             patch.dict(os.environ, {"BRAND_SCHEDULER_ENABLED": "false", "WORKER_QUEUE_URL": "queue"}), \
             patch.object(lambda_worker, "engine", return_value="db"), \
             patch.object(lambda_worker, "mark_stale", return_value=0), \
             patch.object(lambda_worker, "publish_pending", return_value=(2, 0)) as publish, \
             patch.object(lambda_worker, "count_exhausted", return_value=0), \
             patch.object(lambda_worker, "work_once") as worker:
            self.assertEqual(lambda_worker.handler({}, None), {"status": "dispatched", "published": 2, "failed": 0})
        publish.assert_called_once_with("db", sqs, "queue")
        worker.assert_not_called()

    def test_idle_does_not_load_firecrawl_secret(self):
        with patch.dict(os.environ, {"BRAND_SCHEDULER_ENABLED": "false"}), \
             patch.object(lambda_worker, "engine", return_value="db"), \
             patch.object(lambda_worker, "mark_stale", return_value=0) as stale, \
             patch.object(lambda_worker, "work_once", return_value=None) as work:
            self.assertEqual(lambda_worker.handler({}, None), {"status": "idle"})
            stale.assert_called_once_with("db", 30, requeue=False)
            work.assert_called_once_with("db", lambda_worker.provider)

    def test_status_contains_no_secret_or_content(self):
        run_id = uuid4()
        with patch.dict(os.environ, {"BRAND_SCHEDULER_ENABLED": "false"}), \
             patch.object(lambda_worker, "engine", return_value="db"), \
             patch.object(lambda_worker, "mark_stale", return_value=0), \
             patch.object(lambda_worker, "work_once", return_value=(run_id, "success")), \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(lambda_worker.handler({}, None), {"run_id": str(run_id), "status": "success"})
            self.assertEqual(json.loads(output.getvalue()), {"event": "tracking_run", "status": "success", "alert": 0})
            self.assertNotIn(str(run_id), output.getvalue())

    def test_enabled_scheduler_queues_before_worker(self):
        with patch.dict(os.environ, {"BRAND_SCHEDULER_ENABLED": "true"}), \
             patch.object(lambda_worker, "engine", return_value="db"), \
             patch.object(lambda_worker, "mark_stale", return_value=0), \
             patch.object(lambda_worker, "enqueue_due") as schedule, \
             patch.object(lambda_worker, "work_once", return_value=None) as work:
            self.assertEqual(lambda_worker.handler({}, None), {"status": "idle"})
            schedule.assert_called_once_with("db")
            work.assert_called_once_with("db", lambda_worker.provider)

    def test_failure_partial_and_timeout_emit_alerts(self):
        for status in ("failed", "partial"):
            with self.subTest(status=status), \
                 patch.dict(os.environ, {"BRAND_SCHEDULER_ENABLED": "false"}), \
                 patch.object(lambda_worker, "engine", return_value="db"), \
                 patch.object(lambda_worker, "mark_stale", return_value=2), \
                 patch.object(lambda_worker, "work_once", return_value=(uuid4(), status)), \
                 patch("sys.stdout", new_callable=io.StringIO) as output:
                lambda_worker.handler({}, None)
                events = [json.loads(line) for line in output.getvalue().splitlines()]
                self.assertEqual(events, [{"event": "tracking_timeout", "count": 2, "alert": 1},
                                          {"event": "tracking_run", "status": status, "alert": 1}])

    def test_provider_reads_secret_and_applies_call_limit(self):
        client = Mock()
        client.get_secret_value.return_value = {"SecretString": json.dumps({"api_key": "test-key"})}
        boto = SimpleNamespace(client=Mock(return_value=client))
        with patch.dict(sys.modules, {"boto3": boto}), \
             patch.dict(os.environ, {"FIRECRAWL_SECRET_ARN": "secret-id", "WORKER_MAX_CALLS": "2"}), \
             patch.object(lambda_worker, "engine", return_value="database"), \
             patch.object(lambda_worker, "FirecrawlTikTok") as factory:
            lambda_worker.provider()
        client.get_secret_value.assert_called_once_with(SecretId="secret-id")
        args, kwargs = factory.call_args
        self.assertEqual(args, ("test-key",))
        self.assertEqual({key: value for key, value in kwargs.items() if key != "reserve_daily"},
                         {"max_calls": 2, "max_attempts": 1, "search_pages": 1, "comment_pages": 1,
                          "estimated_credit_budget": None, "estimated_credits_per_call": 2})
        self.assertEqual(kwargs["reserve_daily"].args, ("database", 0))

    def test_invalid_secret_fails_without_exposing_value(self):
        client = Mock()
        client.get_secret_value.return_value = {"SecretString": json.dumps({"api_key": ""})}
        with patch.dict(sys.modules, {"boto3": SimpleNamespace(client=Mock(return_value=client))}), \
             patch.dict(os.environ, {"FIRECRAWL_SECRET_ARN": "secret-id"}):
            with self.assertRaisesRegex(ValueError, "Invalid Firecrawl secret"):
                lambda_worker.provider()


if __name__ == "__main__":
    unittest.main()

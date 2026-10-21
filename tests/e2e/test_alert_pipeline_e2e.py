import json
import threading
from http.server import HTTPServer
import socket
from typing import Any
import httpx
from unittest.mock import MagicMock

from main import HealthCheckHandler
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort
from worker.registry import build_registry
from handlers.alerts_budget.handler import BudgetAlertHandler
from handlers.alerts_cost_anomaly.handler import CostAnomalyAlertHandler
from handlers.alerts_toxicity.handler import ToxicityAlertHandler
from handlers.alerts_quality_degradation.handler import QualityDegradationAlertHandler
from handlers.alerts_latency_slo.handler import LatencySloAlertHandler
from handlers.alerts_latency_ttft_regression.handler import LatencyTtftRegressionAlertHandler

def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])

class MockMessage:
    def __init__(self, topic: str, value: bytes, headers_list: list[tuple[str, bytes]] | None = None) -> None:
        self._topic = topic
        self._value = value
        self._headers = headers_list

    def topic(self) -> str:
        return self._topic

    def value(self) -> bytes:
        return self._value

    def error(self) -> Any:
        return None

    def headers(self) -> list[tuple[str, bytes]] | None:
        return self._headers

def _create_full_stack_registry(
    db: DbPort,
    redis: RedisPort,
    slack: SlackPort,
    pd: PagerDutyPort,
    metrics: MetricsPort,
) -> dict:
    budget_handler = BudgetAlertHandler(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )
    cost_anomaly_handler = CostAnomalyAlertHandler(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
    )
    toxicity_handler = ToxicityAlertHandler(
        redis_port=redis,
        slack_port=slack,
    )
    degradation_handler = QualityDegradationAlertHandler(
        redis_port=redis,
        slack_port=slack,
    )
    latency_slo_handler = LatencySloAlertHandler(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
    )
    ttft_handler = LatencyTtftRegressionAlertHandler(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        metrics_port=metrics,
    )

    return build_registry(
        budget_handler=budget_handler.handle,
        cost_anomaly_handler=cost_anomaly_handler.handle,
        toxicity_handler=toxicity_handler.handle,
        degradation_handler=degradation_handler.handle,
        latency_slo_handler=latency_slo_handler.handle,
        latency_ttft_regression_handler=ttft_handler.handle,
    )

def test_e2e_budget_alert_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = _create_full_stack_registry(db, redis, slack, pd, metrics)

    budget_event = {
        "user_id": "usr-12345",
        "service": "billing_service",
        "model": "gpt-4o",
        "event_type": "blocked",
        "timestamp_utc": "2026-10-21T18:00:00Z",
    }
    raw_msg = MockMessage(
        "alerts.budget",
        json.dumps(budget_event).encode("utf-8"),
        [("traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")]
    )

    handler_def = registry[raw_msg.topic()]
    handler_def.handler(json.loads(raw_msg.value().decode("utf-8")))

    db.insert_alert.assert_called_once()
    db_args = db.insert_alert.call_args[1]
    assert db_args["alert_type"] == "budget"
    assert db_args["user_id"] == "usr-12345"
    assert db_args["model"] == "gpt-4o"

    slack.send_channel_message.assert_called_once()

def test_e2e_cost_anomaly_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = _create_full_stack_registry(db, redis, slack, pd, metrics)

    cost_event = {
        "service": "billing_service",
        "model": "claude-3-opus",
        "current_cost": 75.5,
        "ewma_value": 15.2,
        "sample_count": 40,
        "timestamp": "2026-10-21T18:00:00Z",
    }
    raw_msg = MockMessage("alerts.cost.anomaly", json.dumps(cost_event).encode("utf-8"))

    handler_def = registry[raw_msg.topic()]
    handler_def.handler(json.loads(raw_msg.value().decode("utf-8")))

    db.insert_alert.assert_called_once()
    assert db.insert_alert.call_args[1]["alert_type"] == "cost_anomaly"

    pd.trigger_incident.assert_called_once()
    pd_args = pd.trigger_incident.call_args[1]
    assert pd_args["severity"] == "critical"

    slack.send_channel_message.assert_called_once()

def test_e2e_toxicity_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = _create_full_stack_registry(db, redis, slack, pd, metrics)

    toxicity_event = {
        "span_id": "span-unsafe-99",
        "toxicity_score": 0.85,
        "user_id": "usr-bad-actor",
        "model": "toxic-bert",
        "endpoint": "/v1/chat",
    }
    raw_msg = MockMessage("llm.toxicity.flagged", json.dumps(toxicity_event).encode("utf-8"))

    handler_def = registry[raw_msg.topic()]
    handler_def.handler(json.loads(raw_msg.value().decode("utf-8")))

    slack.send_channel_message.assert_called_once()
    slack_call = slack.send_channel_message.call_args[0]
    assert slack_call[0] == "#llm-safety-review"

def test_e2e_quality_degradation_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = _create_full_stack_registry(db, redis, slack, pd, metrics)

    quality_event = {
        "model": "gpt-4o",
        "endpoint": "/v1/chat/completions",
        "current_window_avg": 0.61,
        "baseline": 0.80,
        "ratio": 0.7625,
        "alerted_at": "2026-06-15T08:00:00+00:00",
    }
    raw_msg = MockMessage("alerts.quality.degradation", json.dumps(quality_event).encode("utf-8"))

    handler_def = registry[raw_msg.topic()]
    handler_def.handler(json.loads(raw_msg.value().decode("utf-8")))

    slack.send_channel_message.assert_called_once()
    slack_call = slack.send_channel_message.call_args[0]
    assert slack_call[0] == "#llm-quality-alerts"

def test_e2e_latency_slo_and_ttft_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    redis.get_open_incident.return_value = None
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = _create_full_stack_registry(db, redis, slack, pd, metrics)

    slo_event = {
        "model": "gpt-4",
        "endpoint": "/v1/chat",
        "severity": "page",
        "burn_rate": 2.5,
        "p95_current": 120.0,
        "p95_baseline": 50.0,
        "p99_current": 250.0,
        "p99_baseline": 100.0,
        "budget_remaining": 88.5,
        "timestamp": "2026-06-29T09:00:00Z",
    }
    raw_slo_msg = MockMessage("alerts.latency.slo", json.dumps(slo_event).encode("utf-8"))
    registry[raw_slo_msg.topic()].handler(json.loads(raw_slo_msg.value().decode("utf-8")))

    assert pd.trigger_incident.call_count == 1

    ttft_event = {
        "model": "gemini-1.5-flash",
        "current": 180.0,
        "baseline": 120.0,
        "hour_of_day": 14,
        "timestamp": "2026-07-01T14:00:00Z",
    }
    raw_ttft_msg = MockMessage("alerts.latency.ttft_regression", json.dumps(ttft_event).encode("utf-8"))
    registry[raw_ttft_msg.topic()].handler(json.loads(raw_ttft_msg.value().decode("utf-8")))

    assert db.insert_alert.call_count == 1

def test_e2e_health_server_http_spec() -> None:
    port = _get_free_port()
    server = HTTPServer(("127.0.0.1", port), HealthCheckHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
            resp_liveness = client.get("/healthz")
            assert resp_liveness.status_code == 200
            assert resp_liveness.headers["Content-Type"] == "application/json"
            assert resp_liveness.json()["status"] == "ok"

            resp_readiness = client.get("/readyz")
            assert resp_readiness.status_code == 200
            assert resp_readiness.headers["Content-Type"] == "application/json"
            assert resp_readiness.json()["status"] == "ready"

            resp_invalid = client.get("/invalid-path")
            assert resp_invalid.status_code == 404
    finally:
        server.shutdown()
        server.server_close()

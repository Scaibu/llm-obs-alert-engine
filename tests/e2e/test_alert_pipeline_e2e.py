import json
import threading
from http.server import HTTPServer
import socket
from typing import Any
import httpx
from unittest.mock import MagicMock, patch

from main import HealthCheckHandler, main
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort
from worker.registry import build_registry

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

def test_e2e_budget_alert_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = build_registry(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )

    budget_event = {
        "user_id": "usr-12345",
        "model": "gpt-4o",
        "event_type": "budget_exceeded",
        "timestamp_utc": "2026-10-21T18:00:00Z",
    }
    raw_msg = MockMessage(
        "alerts.budget",
        json.dumps(budget_event).encode("utf-8"),
        [("traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")]
    )

    handler = registry[raw_msg.topic()]
    handler.handle(json.loads(raw_msg.value().decode("utf-8")))

    db.insert_alert.assert_called_once()
    db_args = db.insert_alert.call_args[1]
    assert db_args["alert_type"] == "budget"
    assert db_args["user_id"] == "usr-12345"
    assert db_args["model"] == "gpt-4o"

    slack.send_direct_message.assert_called_once()
    slack_args = slack.send_direct_message.call_args[0]
    assert slack_args[0] == "usr-12345"

def test_e2e_cost_anomaly_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = build_registry(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )

    cost_event = {
        "service": "billing_service",
        "model": "claude-3-opus",
        "current_cost": 75.5,
        "ewma_value": 15.2,
        "sample_count": 40,
        "timestamp": "2026-10-21T18:00:00Z",
    }
    raw_msg = MockMessage("alerts.cost.anomaly", json.dumps(cost_event).encode("utf-8"))

    handler = registry[raw_msg.topic()]
    handler.handle(json.loads(raw_msg.value().decode("utf-8")))

    db.insert_alert.assert_called_once()
    assert db.insert_alert.call_args[1]["alert_type"] == "cost_anomaly"

    pd.trigger_incident.assert_called_once()
    pd_args = pd.trigger_incident.call_args[1]
    assert pd_args["severity"] == "critical"
    assert "cost anomaly" in pd_args["summary"].lower()

    slack.send_channel_message.assert_called_once()

def test_e2e_toxicity_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = build_registry(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )

    toxicity_event = {
        "span_id": "span-unsafe-99",
        "toxicity_score": 0.96,
        "user_id": "usr-bad-actor",
        "model": "gpt-4",
    }
    raw_msg = MockMessage("llm.toxicity.flagged", json.dumps(toxicity_event).encode("utf-8"))

    handler = registry[raw_msg.topic()]
    handler.handle(json.loads(raw_msg.value().decode("utf-8")))

    db.insert_alert.assert_called_once()
    assert db.insert_alert.call_args[1]["alert_type"] == "toxicity"

    slack.send_channel_message.assert_called_once()
    slack_call = slack.send_channel_message.call_args[0]
    assert slack_call[0] == "#llm-safety-alerts"

def test_e2e_quality_degradation_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = build_registry(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )

    quality_event = {
        "service": "recommendation_service",
        "model": "gpt-4o-mini",
        "metric_name": "faithfulness",
        "baseline_value": 0.95,
        "current_value": 0.60,
        "degradation_pct": 36.8,
        "sample_count": 500,
    }
    raw_msg = MockMessage("alerts.quality.degradation", json.dumps(quality_event).encode("utf-8"))

    handler = registry[raw_msg.topic()]
    handler.handle(json.loads(raw_msg.value().decode("utf-8")))

    db.insert_alert.assert_called_once()
    pd.trigger_incident.assert_called_once()
    slack.send_channel_message.assert_called_once()

def test_e2e_latency_slo_and_ttft_pipeline() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    redis.get_open_incident.return_value = None
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    registry = build_registry(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )

    slo_event = {
        "model": "gpt-4",
        "endpoint": "/v1/chat/completions",
        "slo_target_ms": 1000.0,
        "current_p95_ms": 2800.0,
        "sample_count": 200,
    }
    raw_slo_msg = MockMessage("alerts.latency.slo", json.dumps(slo_event).encode("utf-8"))
    registry[raw_slo_msg.topic()].handle(json.loads(raw_slo_msg.value().decode("utf-8")))

    assert db.insert_alert.call_count == 1
    assert pd.trigger_incident.call_count == 1

    ttft_event = {
        "model": "gpt-4",
        "endpoint": "/v1/chat/completions",
        "baseline_ttft_ms": 150.0,
        "current_ttft_ms": 450.0,
        "regression_pct": 200.0,
        "sample_count": 100,
    }
    raw_ttft_msg = MockMessage("alerts.latency.ttft_regression", json.dumps(ttft_event).encode("utf-8"))
    registry[raw_ttft_msg.topic()].handle(json.loads(raw_ttft_msg.value().decode("utf-8")))

    assert db.insert_alert.call_count == 2
    assert pd.trigger_incident.call_count == 2

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

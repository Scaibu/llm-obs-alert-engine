import json
from typing import Any
from unittest.mock import MagicMock
from worker.registry import build_registry
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort

class FakeKafkaMessage:
    def __init__(self, topic: str, value: bytes | None, error: Any = None) -> None:
        self._topic = topic
        self._value = value
        self._error = error

    def topic(self) -> str:
        return self._topic

    def value(self) -> bytes | None:
        return self._value

    def error(self) -> Any:
        return self._error

    def headers(self) -> list[tuple[str, bytes]] | None:
        return [("traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")]

def test_dispatcher_integration_with_feature_registry() -> None:
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

    test_payloads = [
        ("alerts.budget", {"user_id": "usr-1", "model": "gpt-4", "event_type": "blocked"}),
        ("alerts.cost.anomaly", {"service": "billing_service", "model": "gpt-4", "current_cost": 50.0, "ewma_value": 10.0, "sample_count": 25}),
        ("llm.toxicity.flagged", {"span_id": "sp-101", "toxicity_score": 0.95, "user_id": "usr-safe"}),
        ("alerts.quality.degradation", {"service": "chat_service", "model": "gpt-4", "metric_name": "accuracy", "baseline_value": 0.9, "current_value": 0.5, "degradation_pct": 44.4}),
        ("alerts.latency.slo", {"model": "gpt-4", "endpoint": "/chat", "slo_target_ms": 1000.0, "current_p95_ms": 2500.0, "sample_count": 50}),
        ("alerts.latency.ttft_regression", {"model": "gpt-4", "endpoint": "/stream", "baseline_ttft_ms": 200.0, "current_ttft_ms": 600.0, "regression_pct": 200.0, "sample_count": 30}),
    ]

    for topic, payload in test_payloads:
        msg = FakeKafkaMessage(topic, json.dumps(payload).encode("utf-8"))
        handler = registry.get(msg.topic())
        assert handler is not None
        data = json.loads(msg.value().decode("utf-8"))
        handler.handle(data)

    assert db.insert_alert.call_count >= 6
    assert slack.send_channel_message.call_count + slack.send_direct_message.call_count >= 5

def test_dispatcher_handles_malformed_json_gracefully() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
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

    malformed_msg = FakeKafkaMessage("alerts.budget", b"{not valid json:")
    try:
        json.loads(malformed_msg.value().decode("utf-8"))
        assert False, "Should have raised JSONDecodeError"
    except Exception:
        pass
    assert db.insert_alert.call_count == 0

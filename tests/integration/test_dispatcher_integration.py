import json
from typing import Any
from unittest.mock import MagicMock
import pytest
from worker.registry import build_registry
from handlers.alerts_budget.handler import BudgetAlertHandler
from handlers.alerts_cost_anomaly.handler import CostAnomalyAlertHandler
from handlers.alerts_toxicity.handler import ToxicityAlertHandler
from handlers.alerts_quality_degradation.handler import QualityDegradationAlertHandler
from handlers.alerts_latency_slo.handler import LatencySloAlertHandler
from handlers.alerts_latency_ttft_regression.handler import LatencyTtftRegressionAlertHandler
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

    registry = build_registry(
        budget_handler=budget_handler.handle,
        cost_anomaly_handler=cost_anomaly_handler.handle,
        toxicity_handler=toxicity_handler.handle,
        degradation_handler=degradation_handler.handle,
        latency_slo_handler=latency_slo_handler.handle,
        latency_ttft_regression_handler=ttft_handler.handle,
    )

    test_payloads = [
        ("alerts.budget", {"user_id": "usr-1", "model": "gpt-4", "event_type": "blocked"}),
        ("alerts.cost.anomaly", {"service": "billing_service", "model": "gpt-4", "current_cost": 50.0, "ewma_value": 10.0, "sample_count": 25}),
        ("llm.toxicity.flagged", {"span_id": "sp-101", "toxicity_score": 0.95, "user_id": "usr-safe", "model": "gpt-4", "endpoint": "/chat"}),
        ("alerts.quality.degradation", {"model": "gpt-4o", "endpoint": "/chat", "current_window_avg": 0.6, "baseline": 0.9, "ratio": 0.66, "alerted_at": "2026-06-15T08:00:00Z"}),
        ("alerts.latency.slo", {"model": "gpt-4", "endpoint": "/chat", "severity": "ticket", "burn_rate": 2.5, "p95_current": 120.0, "p95_baseline": 50.0, "p99_current": 250.0, "p99_baseline": 100.0, "budget_remaining": 88.5, "timestamp": "2026-06-29T09:00:00Z"}),
        ("alerts.latency.ttft_regression", {"model": "gpt-4", "current": 180.0, "baseline": 120.0, "hour_of_day": 14, "timestamp": "2026-07-01T14:00:00Z"}),
    ]

    for topic, payload in test_payloads:
        msg = FakeKafkaMessage(topic, json.dumps(payload).encode("utf-8"))
        handler_def = registry.get(msg.topic())
        assert handler_def is not None
        raw_val = msg.value()
        assert raw_val is not None
        data = json.loads(raw_val.decode("utf-8"))
        handler_def.handler(data)

    assert db.insert_alert.call_count == 4
    assert slack.send_channel_message.call_count >= 2

def test_dispatcher_handles_malformed_json_gracefully() -> None:
    malformed_msg = FakeKafkaMessage("alerts.budget", b"{not valid json:")
    value = malformed_msg.value()
    assert value is not None
    decoded = value.decode("utf-8")
    with pytest.raises(json.JSONDecodeError):
        json.loads(decoded)

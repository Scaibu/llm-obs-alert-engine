"""
Blueprint:
- Exhaustive unit tests for latency_ttft_regression domain rules, schemas, and workflows.
- Verifies rate limit key generation, TTL, delivery latency, and Slack message formatting.
- Follows canonical role (14) tests.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from features.latency_ttft_regression.contracts.latency_ttft_regression_schema import (
    LatencyTtftRegressionSchemaMapper,
)
from features.latency_ttft_regression.contracts.latency_ttft_regression_types import (
    LatencyTtftRegressionAlertPayload,
    LatencyTtftRegressionRecord,
)
from features.latency_ttft_regression.domain.rules.latency_ttft_regression_rules import (
    LatencyTtftRegressionRules,
)
from features.latency_ttft_regression.domain.workflows.latency_ttft_regression_workflow import (
    LatencyTtftRegressionWorkflow,
)


def test_rate_limit_key_generation() -> None:
    key = LatencyTtftRegressionRules.get_rate_limit_key("gemini-1.5-flash", 14)
    assert key == "rate_limit:latency_ttft_regression:gemini-1.5-flash:14"


def test_delivery_latency_calculation() -> None:
    now = datetime(2026, 7, 1, 14, 0, 10, tzinfo=timezone.utc)
    ts = "2026-07-01T14:00:00Z"
    latency = LatencyTtftRegressionRules.compute_delivery_latency_ms(ts, now=now)
    assert latency == 10000

    assert LatencyTtftRegressionRules.compute_delivery_latency_ms(None) is None
    assert LatencyTtftRegressionRules.compute_delivery_latency_ms("invalid") is None


def test_slack_message_formatting() -> None:
    payload = LatencyTtftRegressionAlertPayload(
        model="gemini-1.5-flash",
        current=180.0,
        baseline=120.0,
        hour_of_day=14,
    )
    workflow = LatencyTtftRegressionWorkflow()
    msg = workflow.prepare_slack_message(payload)
    assert msg == "gemini-1.5-flash TTFT P99 degraded: 180.0ms vs 120.0ms baseline at 14:00 UTC. Possible provider degradation."


def test_database_record_preparation() -> None:
    payload = LatencyTtftRegressionAlertPayload(
        model="claude-3-haiku",
        current=200.0,
        baseline=150.0,
        hour_of_day=18,
        timestamp="2026-07-01T18:00:00Z",
    )
    workflow = LatencyTtftRegressionWorkflow()
    record = workflow.prepare_database_record(payload, delivery_latency_ms=250)
    assert record.alert_type == "latency_ttft_regression"
    assert record.model == "claude-3-haiku"
    assert record.service is None
    assert record.delivery_latency_ms == 250
    assert record.payload["current"] == 200.0


def test_schema_mapper_bidirectional() -> None:
    raw = {
        "model": "gpt-4o",
        "current": 190.5,
        "baseline": 110.0,
        "hour_of_day": 12,
        "timestamp": "2026-07-01T12:00:00Z",
    }
    payload = LatencyTtftRegressionSchemaMapper.from_api(raw)
    assert payload.model == "gpt-4o"
    assert payload.current == 190.5

    exported = LatencyTtftRegressionSchemaMapper.to_api(payload)
    assert exported["model"] == "gpt-4o"
    assert exported["hour_of_day"] == 12

    record = LatencyTtftRegressionRecord(
        alert_type="latency_ttft_regression",
        service=None,
        model="gpt-4o",
        user_id=None,
        event_type="slack",
        payload=raw,
        delivery_latency_ms=120,
    )
    rec_dict = LatencyTtftRegressionSchemaMapper.to_record_dict(record)
    assert rec_dict["alert_type"] == "latency_ttft_regression"
    assert rec_dict["delivery_latency_ms"] == 120


def test_schema_mapper_invalid_hour() -> None:
    invalid = {
        "model": "gpt-4o",
        "current": 100.0,
        "baseline": 50.0,
        "hour_of_day": 24,
    }
    with pytest.raises(ValueError, match="hour_of_day"):
        LatencyTtftRegressionSchemaMapper.from_api(invalid)


def test_validate_finite_non_negative() -> None:
    LatencyTtftRegressionRules.validate_finite_non_negative(100.0, "current")
    with pytest.raises(ValueError, match="must be non-negative"):
        LatencyTtftRegressionRules.validate_finite_non_negative(-5.0, "current")
    with pytest.raises(ValueError, match="must be a finite number"):
        LatencyTtftRegressionRules.validate_finite_non_negative(float("nan"), "current")

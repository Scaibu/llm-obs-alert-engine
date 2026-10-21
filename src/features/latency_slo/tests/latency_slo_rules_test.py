"""
Blueprint:
- Exhaustive unit tests for latency_slo domain rules, schemas, and workflows.
- Verifies severity routing, decision tables, metric calculations, and payload serialization.
- Follows canonical role (14) tests.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from features.latency_slo.contracts.latency_slo_schema import LatencySloSchemaMapper
from features.latency_slo.contracts.latency_slo_types import (
    LatencySloAlertPayload,
    LatencySloAlertRecord,
)
from features.latency_slo.domain.rules.latency_slo_rules import LatencySloRules
from features.latency_slo.domain.workflows.latency_slo_workflow import (
    LatencySloWorkflow,
)


def test_rate_limit_key_generation() -> None:
    key = LatencySloRules.get_page_rate_limit_key("gpt-4", "/v1/chat")
    assert key == "rate_limit:latency_slo_page:gpt-4:/v1/chat"


def test_delivery_latency_calculation() -> None:
    now = datetime(2026, 7, 1, 12, 0, 5, tzinfo=timezone.utc)
    ts = "2026-07-01T12:00:00Z"
    latency = LatencySloRules.compute_delivery_latency_ms(ts, now=now)
    assert latency == 5000

    assert LatencySloRules.compute_delivery_latency_ms(None) is None
    assert LatencySloRules.compute_delivery_latency_ms("invalid-timestamp") is None


def test_workflow_route_evaluation() -> None:
    workflow = LatencySloWorkflow()
    assert workflow.evaluate_route("page") == "page"
    assert workflow.evaluate_route("slack") == "slack"
    assert workflow.evaluate_route("ticket") == "ticket"
    assert workflow.evaluate_route(None) == "resolve"
    assert workflow.evaluate_route("None") == "resolve"
    assert workflow.evaluate_route("") == "resolve"
    assert workflow.evaluate_route("unknown") == "noop"


def test_slack_messages_formatting() -> None:
    payload = LatencySloAlertPayload(
        model="claude-3-5-sonnet",
        endpoint="/v1/completions",
        severity="slack",
        burn_rate=3.14,
        p95_current=120.0,
        p95_baseline=50.0,
        p99_current=200.0,
        p99_baseline=100.0,
        budget_remaining=80.5,
    )
    workflow = LatencySloWorkflow()
    msg = workflow.prepare_slack_breach_message(payload)
    assert "claude-3-5-sonnet" in msg
    assert "3.14" in msg
    assert "80.50%" in msg

    resolve_msg = workflow.prepare_slack_resolve_message("claude-3-5-sonnet", "/v1/completions")
    assert "claude-3-5-sonnet//v1/completions SLO burn rate normalized" in resolve_msg


def test_pagerduty_payload_formatting() -> None:
    payload = LatencySloAlertPayload(
        model="gpt-4o",
        endpoint="/v1/chat",
        severity="page",
        burn_rate=2.5,
        p95_current=100.0,
        p95_baseline=40.0,
        p99_current=180.0,
        p99_baseline=80.0,
        budget_remaining=70.0,
    )
    workflow = LatencySloWorkflow()
    title, details = workflow.prepare_pagerduty_payload(payload)
    assert title == "Latency SLO breach: gpt-4o//v1/chat"
    assert details["model"] == "gpt-4o"
    assert details["burn_rate"] == 2.5
    assert details["budget_remaining"] == 70.0


def test_schema_mapper_bidirectional() -> None:
    raw = {
        "model": "gpt-4",
        "endpoint": "/v1/chat",
        "severity": "slack",
        "burn_rate": 2.1,
        "p95_current": 100.0,
        "p95_baseline": 50.0,
        "p99_current": 200.0,
        "p99_baseline": 100.0,
        "budget_remaining": 90.0,
        "timestamp": "2026-06-29T09:00:00Z",
    }
    payload = LatencySloSchemaMapper.from_api(raw)
    assert payload.model == "gpt-4"
    assert payload.burn_rate == 2.1

    exported = LatencySloSchemaMapper.to_api(payload)
    assert exported["model"] == "gpt-4"
    assert exported["burn_rate"] == 2.1

    record = LatencySloAlertRecord(
        alert_type="latency_slo",
        service="/v1/chat",
        model="gpt-4",
        user_id=None,
        event_type="ticket",
        payload=raw,
        delivery_latency_ms=150,
    )
    record_dict = LatencySloSchemaMapper.to_record_dict(record)
    assert record_dict["alert_type"] == "latency_slo"
    assert record_dict["delivery_latency_ms"] == 150


def test_validate_finite_numbers() -> None:
    LatencySloRules.validate_finite(100.5, "burn_rate")
    with pytest.raises(ValueError):
        LatencySloRules.validate_finite(float("nan"), "burn_rate")
    with pytest.raises(ValueError):
        LatencySloRules.validate_finite(float("inf"), "burn_rate")

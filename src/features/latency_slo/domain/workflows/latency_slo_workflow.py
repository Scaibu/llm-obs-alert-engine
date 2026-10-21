"""
Blueprint:
- Multi-step DAG workflow for processing latency SLO alerts.
- Follows canonical role (09) workflow.
- Coordinates evaluation of alert routing, payload preparation, and notification formatting.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from typing import Any, Optional
from features.latency_slo.contracts.latency_slo_types import (
    LatencySloAlertPayload,
    LatencySloAlertRecord,
)
from features.latency_slo.domain.rules.latency_slo_rules import LatencySloRules


class LatencySloWorkflow:
    def evaluate_route(self, severity: Optional[str]) -> str:
        if LatencySloRules.is_page_severity(severity):
            return "page"
        if LatencySloRules.is_auto_resolve(severity):
            return "resolve"
        if LatencySloRules.is_slack_severity(severity):
            return "slack"
        if LatencySloRules.is_ticket_severity(severity):
            return "ticket"
        return "noop"

    def calculate_delivery_latency(self, timestamp: Optional[str]) -> Optional[int]:
        return LatencySloRules.compute_delivery_latency_ms(timestamp)

    def prepare_pagerduty_payload(
        self, payload: LatencySloAlertPayload
    ) -> tuple[str, dict[str, Any]]:
        title = LatencySloRules.format_pagerduty_title(payload.model, payload.endpoint)
        details = LatencySloRules.format_pagerduty_custom_details(payload)
        return title, details

    def prepare_slack_breach_message(self, payload: LatencySloAlertPayload) -> str:
        return LatencySloRules.format_slack_breach_message(payload)

    def prepare_slack_resolve_message(self, model: str, endpoint: str) -> str:
        return LatencySloRules.format_slack_resolve_message(model, endpoint)

    def prepare_database_record(
        self, payload: LatencySloAlertPayload, delivery_latency_ms: Optional[int]
    ) -> LatencySloAlertRecord:
        db_payload = LatencySloRules.format_database_payload(payload)
        return LatencySloAlertRecord(
            alert_type="latency_slo",
            service=payload.endpoint,
            model=payload.model,
            user_id=None,
            event_type="ticket",
            payload=db_payload,
            delivery_latency_ms=delivery_latency_ms,
        )

"""
Blueprint:
- Pure business logic rules and decision tables for latency_slo alert processing.
- Handles severity routing evaluation, rate limit calculations, metric deltas, and notification formatting.
- Follows canonical role (07) rules.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional
from features.latency_slo.contracts.latency_slo_types import LatencySloAlertPayload


class LatencySloRules:
    RATE_LIMIT_PAGE_TTL_SECONDS: int = 900
    INCIDENT_TTL_SECONDS: int = 86400
    SLACK_ALERTS_CHANNEL: str = "#llm-latency-alerts"
    SOURCE_ALERT_ENGINE: str = "alert-engine"
    SEVERITY_PAGE: str = "page"
    SEVERITY_SLACK: str = "slack"
    SEVERITY_TICKET: str = "ticket"

    @classmethod
    def validate_finite(cls, value: float, field_name: str) -> None:
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"{field_name} must be a finite number, got {value}")

    @classmethod
    def get_page_rate_limit_key(cls, model: str, endpoint: str) -> str:
        return f"rate_limit:latency_slo_page:{model}:{endpoint}"

    @classmethod
    def compute_delivery_latency_ms(
        cls, timestamp: Optional[str], now: Optional[datetime] = None
    ) -> Optional[int]:
        if not timestamp:
            return None
        current_time = now or datetime.now(timezone.utc)
        try:
            normalized = timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            diff = (current_time - dt).total_seconds() * 1000
            return max(0, int(diff))
        except Exception:
            return None

    @classmethod
    def is_page_severity(cls, severity: Optional[str]) -> bool:
        return severity == cls.SEVERITY_PAGE

    @classmethod
    def is_auto_resolve(cls, severity: Optional[str]) -> bool:
        return severity is None or severity == "None" or severity == ""

    @classmethod
    def is_slack_severity(cls, severity: Optional[str]) -> bool:
        return severity == cls.SEVERITY_SLACK

    @classmethod
    def is_ticket_severity(cls, severity: Optional[str]) -> bool:
        return severity == cls.SEVERITY_TICKET

    @classmethod
    def format_pagerduty_title(cls, model: str, endpoint: str) -> str:
        return f"Latency SLO breach: {model}/{endpoint}"

    @classmethod
    def format_pagerduty_custom_details(
        cls, payload: LatencySloAlertPayload
    ) -> dict[str, Any]:
        return {
            "model": payload.model,
            "endpoint": payload.endpoint,
            "burn_rate": payload.burn_rate,
            "p95_current": payload.p95_current,
            "p95_baseline": payload.p95_baseline,
            "p99_current": payload.p99_current,
            "p99_baseline": payload.p99_baseline,
            "budget_remaining": payload.budget_remaining,
        }

    @classmethod
    def format_slack_breach_message(cls, payload: LatencySloAlertPayload) -> str:
        return (
            f"*Latency SLO Breach*\n"
            f"*Model:* `{payload.model}`\n"
            f"*Endpoint:* `{payload.endpoint}`\n"
            f"*Burn Rate:* `{payload.burn_rate:.2f}`\n"
            f"*P95 Current vs Baseline:* `{payload.p95_current:.2f}ms` / `{payload.p95_baseline:.2f}ms`\n"
            f"*P99 Current vs Baseline:* `{payload.p99_current:.2f}ms` / `{payload.p99_baseline:.2f}ms`\n"
            f"*Budget Remaining:* `{payload.budget_remaining:.2f}%`"
        )

    @classmethod
    def format_slack_resolve_message(cls, model: str, endpoint: str) -> str:
        return f"{model}/{endpoint} SLO burn rate normalized. Incident auto-resolved."

    @classmethod
    def format_database_payload(cls, payload: LatencySloAlertPayload) -> dict[str, Any]:
        return {
            "model": payload.model,
            "endpoint": payload.endpoint,
            "severity": payload.severity,
            "burn_rate": payload.burn_rate,
            "p95_current": payload.p95_current,
            "p95_baseline": payload.p95_baseline,
            "p99_current": payload.p99_current,
            "p99_baseline": payload.p99_baseline,
            "budget_remaining": payload.budget_remaining,
            "timestamp": payload.timestamp,
        }

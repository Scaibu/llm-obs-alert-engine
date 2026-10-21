"""
Blueprint:
- Pure business logic rules and decision tables for latency_ttft_regression alert processing.
- Handles rate-limiting keys, metric deltas, validation, and Slack message formatting.
- Follows canonical role (07) rules.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional
from features.latency_ttft_regression.contracts.latency_ttft_regression_types import (
    LatencyTtftRegressionAlertPayload,
)


class LatencyTtftRegressionRules:
    RATE_LIMIT_TTL_SECONDS: int = 21600
    SLACK_ALERTS_CHANNEL: str = "#llm-latency-alerts"
    ALERT_TYPE: str = "latency_ttft_regression"
    EVENT_TYPE: str = "slack"
    MAX_HOUR_OF_DAY: int = 23

    @classmethod
    def validate_finite_non_negative(cls, value: float, field_name: str) -> None:
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"{field_name} must be a finite number, got {value}")
        if value < 0.0:
            raise ValueError(f"{field_name} must be non-negative, got {value}")

    @classmethod
    def validate_hour_of_day(cls, hour_of_day: int) -> None:
        if not (0 <= hour_of_day <= cls.MAX_HOUR_OF_DAY):
            raise ValueError(
                f"hour_of_day must be between 0 and {cls.MAX_HOUR_OF_DAY}, got {hour_of_day}"
            )

    @classmethod
    def get_rate_limit_key(cls, model: str, hour_of_day: int) -> str:
        return f"rate_limit:latency_ttft_regression:{model}:{hour_of_day}"

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
    def format_slack_message(cls, payload: LatencyTtftRegressionAlertPayload) -> str:
        return (
            f"{payload.model} TTFT P99 degraded: {payload.current}ms vs "
            f"{payload.baseline}ms baseline at {payload.hour_of_day}:00 UTC. "
            f"Possible provider degradation."
        )

    @classmethod
    def format_database_payload(
        cls, payload: LatencyTtftRegressionAlertPayload
    ) -> dict[str, Any]:
        return {
            "model": payload.model,
            "current": payload.current,
            "baseline": payload.baseline,
            "hour_of_day": payload.hour_of_day,
            "timestamp": payload.timestamp,
        }

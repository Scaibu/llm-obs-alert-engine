"""
Blueprint:
- Pure domain models, input/output DTOs, and error types for latency_ttft_regression.
- Follows canonical role (04) types.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class LatencyTtftRegressionAlertPayload:
    model: str
    current: float
    baseline: float
    hour_of_day: int
    timestamp: Optional[str] = None


@dataclass
class LatencyTtftRegressionRecord:
    alert_type: str
    service: Optional[str]
    model: Optional[str]
    user_id: Optional[str]
    event_type: Optional[str]
    payload: dict[str, Any]
    delivery_latency_ms: Optional[int] = None


__all__ = [
    "LatencyTtftRegressionAlertPayload",
    "LatencyTtftRegressionRecord",
]

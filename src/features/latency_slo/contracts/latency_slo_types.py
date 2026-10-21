"""
Blueprint:
- Pure domain models, input/output DTOs, and error types for latency_slo feature.
- Follows canonical role (04) types.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LatencySloAlertPayload:
    model: str
    endpoint: str
    severity: str
    burn_rate: float = 0.0
    p95_current: float = 0.0
    p95_baseline: float = 0.0
    p99_current: float = 0.0
    p99_baseline: float = 0.0
    budget_remaining: float = 0.0
    timestamp: Optional[str] = None


@dataclass
class LatencySloAlertRecord:
    alert_type: str
    service: Optional[str]
    model: Optional[str]
    user_id: Optional[str]
    event_type: Optional[str]
    payload: dict[str, Any]
    delivery_latency_ms: Optional[int] = None


@dataclass(frozen=True)
class SloBreachDetails:
    model: str
    endpoint: str
    burn_rate: float
    p95_current: float
    p95_baseline: float
    p99_current: float
    p99_baseline: float
    budget_remaining: float


__all__ = [
    "LatencySloAlertPayload",
    "LatencySloAlertRecord",
    "SloBreachDetails",
]

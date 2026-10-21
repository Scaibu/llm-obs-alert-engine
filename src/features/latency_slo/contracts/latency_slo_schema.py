"""
Blueprint:
- Validation and Anti-Corruption Layer (ACL) for latency_slo domain models.
- Follows canonical role (03) schema.
- Bidirectional mapping fromApi and toApi, validating incoming payloads.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from typing import Any, Mapping
from features.latency_slo.contracts.latency_slo_types import (
    LatencySloAlertPayload,
    LatencySloAlertRecord,
)


class LatencySloSchemaMapper:
    @staticmethod
    def from_api(data: Mapping[str, Any]) -> LatencySloAlertPayload:
        model = str(data.get("model") or "unknown")
        endpoint = str(data.get("endpoint") or "unknown")
        raw_severity = data.get("severity")
        severity = "ticket" if raw_severity is None else str(raw_severity)
        burn_rate = float(data.get("burn_rate", 0.0))
        p95_current = float(data.get("p95_current", 0.0))
        p95_baseline = float(data.get("p95_baseline", 0.0))
        p99_current = float(data.get("p99_current", 0.0))
        p99_baseline = float(data.get("p99_baseline", 0.0))
        budget_remaining = float(data.get("budget_remaining", 0.0))
        timestamp = data.get("timestamp")
        return LatencySloAlertPayload(
            model=model,
            endpoint=endpoint,
            severity=severity,
            burn_rate=burn_rate,
            p95_current=p95_current,
            p95_baseline=p95_baseline,
            p99_current=p99_current,
            p99_baseline=p99_baseline,
            budget_remaining=budget_remaining,
            timestamp=str(timestamp) if timestamp is not None else None,
        )

    @staticmethod
    def to_api(payload: LatencySloAlertPayload) -> dict[str, Any]:
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

    @staticmethod
    def to_record_dict(record: LatencySloAlertRecord) -> dict[str, Any]:
        return {
            "alert_type": record.alert_type,
            "service": record.service,
            "model": record.model,
            "user_id": record.user_id,
            "event_type": record.event_type,
            "payload": record.payload,
            "delivery_latency_ms": record.delivery_latency_ms,
        }

"""
Blueprint:
- Validation and Anti-Corruption Layer (ACL) for latency_ttft_regression domain models.
- Follows canonical role (03) schema.
- Bidirectional mapping fromApi and toApi, validating incoming payloads.
"""

from __future__ import annotations

from typing import Any, Mapping
from features.latency_ttft_regression.contracts.latency_ttft_regression_types import (
    LatencyTtftRegressionAlertPayload,
    LatencyTtftRegressionRecord,
)


class LatencyTtftRegressionSchemaMapper:
    @staticmethod
    def from_api(data: Mapping[str, Any]) -> LatencyTtftRegressionAlertPayload:
        model = str(data.get("model") or "unknown")
        current = float(data.get("current", 0.0))
        baseline = float(data.get("baseline", 0.0))
        hour_of_day = int(data.get("hour_of_day", 0))
        if not (0 <= hour_of_day <= 23):
            raise ValueError(f"hour_of_day must be between 0 and 23, got {hour_of_day}")
        timestamp = data.get("timestamp")
        return LatencyTtftRegressionAlertPayload(
            model=model,
            current=current,
            baseline=baseline,
            hour_of_day=hour_of_day,
            timestamp=str(timestamp) if timestamp is not None else None,
        )

    @staticmethod
    def to_api(payload: LatencyTtftRegressionAlertPayload) -> dict[str, Any]:
        return {
            "model": payload.model,
            "current": payload.current,
            "baseline": payload.baseline,
            "hour_of_day": payload.hour_of_day,
            "timestamp": payload.timestamp,
        }

    @staticmethod
    def to_record_dict(record: LatencyTtftRegressionRecord) -> dict[str, Any]:
        return {
            "alert_type": record.alert_type,
            "service": record.service,
            "model": record.model,
            "user_id": record.user_id,
            "event_type": record.event_type,
            "payload": record.payload,
            "delivery_latency_ms": record.delivery_latency_ms,
        }

"""
Blueprint:
- Resilient outbound adapter for latency_ttft_regression alert persistence.
- Implements LatencyTtftRegressionRepositoryPort using DbPort.
- Follows canonical role (11) adapters.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from typing import Any, Optional
from features.latency_ttft_regression.contracts.latency_ttft_regression_types import (
    LatencyTtftRegressionRecord,
)
from features.latency_ttft_regression.infrastructure.ports.latency_ttft_regression_repository_port import (
    LatencyTtftRegressionRepositoryPort,
)
from shared.ports.db_port import DbPort


class LatencyTtftRegressionRepositoryAdapter(LatencyTtftRegressionRepositoryPort):
    def __init__(self, db_port: DbPort) -> None:
        self._db_port = db_port

    def save_alert(
        self, record: LatencyTtftRegressionRecord, trace_id: str = ""
    ) -> None:
        self._db_port.insert_alert(
            alert_type=record.alert_type,
            service=record.service,
            model=record.model,
            user_id=record.user_id,
            event_type=record.event_type,
            payload=record.payload,
            delivery_latency_ms=record.delivery_latency_ms,
        )

    def get_alert(self, alert_id: str, trace_id: str = "") -> Optional[dict[str, Any]]:
        return None

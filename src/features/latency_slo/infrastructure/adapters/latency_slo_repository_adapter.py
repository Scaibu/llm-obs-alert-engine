"""
Blueprint:
- Resilient outbound adapter for latency_slo alert persistence.
- Implements LatencySloRepositoryPort using DbPort.
- Follows canonical role (11) adapters.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from typing import Any, Optional
from features.latency_slo.contracts.latency_slo_types import LatencySloAlertRecord
from features.latency_slo.infrastructure.ports.latency_slo_repository_port import (
    LatencySloRepositoryPort,
)
from shared.ports.db_port import DbPort


class LatencySloRepositoryAdapter(LatencySloRepositoryPort):
    def __init__(self, db_port: DbPort) -> None:
        self._db_port = db_port

    def save_alert(self, record: LatencySloAlertRecord, trace_id: str = "") -> None:
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

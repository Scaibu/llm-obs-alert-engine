"""
Blueprint:
- Abstract hexagonal outbound port interface for latency_slo alert persistence.
- Follows canonical role (10) ports.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from features.latency_slo.contracts.latency_slo_types import LatencySloAlertRecord


class LatencySloRepositoryPort(ABC):
    @abstractmethod
    def save_alert(self, record: LatencySloAlertRecord, trace_id: str = "") -> None:
        raise NotImplementedError

    @abstractmethod
    def get_alert(self, alert_id: str, trace_id: str = "") -> Optional[dict[str, Any]]:
        raise NotImplementedError

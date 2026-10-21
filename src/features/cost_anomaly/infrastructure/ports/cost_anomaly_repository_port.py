from abc import ABC, abstractmethod
from typing import Any

class CostAnomalyRepositoryPort(ABC):
    @abstractmethod
    def record_alert(
        self,
        alert_type: str,
        service: str,
        model: str,
        user_id: str | None,
        event_type: str,
        payload: dict[str, Any],
        delivery_latency_ms: int | None,
    ) -> None:
        pass

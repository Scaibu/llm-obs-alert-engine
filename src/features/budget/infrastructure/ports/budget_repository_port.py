from abc import ABC, abstractmethod
from typing import Any

class BudgetRepositoryPort(ABC):
    @abstractmethod
    def record_alert(
        self,
        alert_type: str,
        service: str | None,
        model: str,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
        delivery_latency_ms: int | None,
    ) -> None:
        pass

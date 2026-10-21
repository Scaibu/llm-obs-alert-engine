from abc import ABC, abstractmethod
from typing import Any

class ToxicityRepositoryPort(ABC):
    @abstractmethod
    def record_alert(
        self,
        alert_type: str,
        span_id: str,
        user_id: str,
        endpoint: str,
        model: str,
        toxicity_score: float,
        payload: dict[str, Any],
    ) -> None:
        pass

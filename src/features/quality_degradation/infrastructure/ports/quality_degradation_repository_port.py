from abc import ABC, abstractmethod
from typing import Any

class QualityDegradationRepositoryPort(ABC):
    @abstractmethod
    def record_alert(
        self,
        alert_type: str,
        model: str,
        endpoint: str,
        payload: dict[str, Any],
    ) -> None:
        pass

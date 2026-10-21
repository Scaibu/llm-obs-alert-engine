from typing import Any
from features.quality_degradation.infrastructure.ports.quality_degradation_repository_port import QualityDegradationRepositoryPort
from shared.repositories.base_alert_repository import BaseAlertRepository

class QualityDegradationRepositoryAdapter(BaseAlertRepository, QualityDegradationRepositoryPort):
    def record_alert(
        self,
        alert_type: str,
        model: str,
        endpoint: str,
        payload: dict[str, Any],
    ) -> None:
        self.insert_alert_history(
            alert_type=alert_type,
            model=model,
            payload=payload,
        )

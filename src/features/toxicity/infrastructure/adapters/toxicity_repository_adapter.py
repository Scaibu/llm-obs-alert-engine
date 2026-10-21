from typing import Any
from features.toxicity.infrastructure.ports.toxicity_repository_port import ToxicityRepositoryPort
from shared.repositories.base_alert_repository import BaseAlertRepository

class ToxicityRepositoryAdapter(BaseAlertRepository, ToxicityRepositoryPort):
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
        self.insert_alert_history(
            alert_type=alert_type,
            model=model,
            user_id=user_id,
            payload=payload,
        )

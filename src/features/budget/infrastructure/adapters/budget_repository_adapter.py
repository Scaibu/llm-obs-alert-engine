from typing import Any
from features.budget.infrastructure.ports.budget_repository_port import BudgetRepositoryPort
from shared.repositories.base_alert_repository import BaseAlertRepository

class BudgetRepositoryAdapter(BaseAlertRepository, BudgetRepositoryPort):
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
        self.insert_alert_history(
            alert_type=alert_type,
            service=service,
            model=model,
            user_id=user_id,
            event_type=event_type,
            payload=payload,
            delivery_latency_ms=delivery_latency_ms,
        )

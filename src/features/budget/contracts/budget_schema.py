from typing import Any
from features.budget.contracts.budget_types import BudgetAlertPayload, BudgetAlertResult, BudgetValidationError

class BudgetSchemaMapper:
    @staticmethod
    def from_api(data: dict[str, Any]) -> BudgetAlertPayload:
        user_id = data.get("user_id")
        model = data.get("model")
        event_type = data.get("event_type")
        service = data.get("service")
        timestamp_utc = data.get("timestamp_utc")

        if not user_id or not isinstance(user_id, str):
            raise BudgetValidationError("Missing or invalid user_id")
        if not model or not isinstance(model, str):
            raise BudgetValidationError("Missing or invalid model")
        if not event_type or not isinstance(event_type, str):
            raise BudgetValidationError("Missing or invalid event_type")

        return BudgetAlertPayload(
            user_id=user_id,
            model=model,
            event_type=event_type,
            service=service if isinstance(service, str) else None,
            timestamp_utc=timestamp_utc if isinstance(timestamp_utc, str) else None,
        )

    @staticmethod
    def to_api(result: BudgetAlertResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "rate_limited": result.rate_limited,
            "message": result.message,
            "severity": result.severity,
            "delivery_latency_ms": result.delivery_latency_ms,
        }

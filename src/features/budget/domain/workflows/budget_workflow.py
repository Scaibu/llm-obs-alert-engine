from features.budget.contracts.budget_types import BudgetAlertPayload, BudgetAlertResult
from features.budget.domain.rules.budget_rules import BudgetRules

class BudgetWorkflow:
    @staticmethod
    def execute(payload: BudgetAlertPayload, is_rate_limited: bool) -> BudgetAlertResult:
        if is_rate_limited:
            return BudgetAlertResult(status="rate_limited", rate_limited=True)

        message = BudgetRules.format_alert_message(
            user_id=payload.user_id,
            model=payload.model,
            event_type=payload.event_type,
        )
        latency_ms = BudgetRules.calculate_delivery_latency_ms(payload.timestamp_utc)
        severity = BudgetRules.get_severity(payload.event_type)

        return BudgetAlertResult(
            status="processed",
            rate_limited=False,
            message=message,
            severity=severity,
            delivery_latency_ms=latency_ms,
        )

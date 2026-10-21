from datetime import datetime, timezone

class BudgetRules:
    RATE_LIMIT_TTL_SECONDS: int = 900
    SLACK_COST_ALERTS_CHANNEL: str = "#llm-cost-alerts"

    @staticmethod
    def get_rate_limit_key(user_id: str, model: str) -> str:
        return f"rate_limit:budget_alert:{user_id}:{model}"

    @staticmethod
    def get_severity(event_type: str) -> str:
        return "critical" if event_type == "blocked" else "warning"

    @staticmethod
    def format_alert_message(user_id: str, model: str, event_type: str) -> str:
        if event_type == "blocked":
            return f"Budget exceeded: user '{user_id}' blocked for model '{model}'."
        return f"Budget warning: user '{user_id}' has consumed 80% of budget for model '{model}'."

    @staticmethod
    def calculate_delivery_latency_ms(timestamp_utc: str | None) -> int | None:
        if not timestamp_utc:
            return None
        try:
            ts = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max(0, int((now - ts).total_seconds() * 1000))
        except Exception:
            return None

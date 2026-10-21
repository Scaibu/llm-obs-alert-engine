class QualityDegradationRules:
    RATE_LIMIT_TTL_SECONDS: int = 3600
    SLACK_QUALITY_ALERTS_CHANNEL: str = "#llm-quality-alerts"

    @staticmethod
    def get_rate_limit_key(model: str, endpoint: str) -> str:
        return f"rate_limit:quality_degradation:{model}:{endpoint}"

    @staticmethod
    def format_alert_message(
        model: str,
        endpoint: str,
        current_window_avg: float,
        baseline: float,
        ratio: float,
        alerted_at: str,
    ) -> str:
        return (
            f"Quality degradation alert: model={model} endpoint={endpoint} "
            f"current_avg={current_window_avg:.4f} baseline={baseline:.4f} "
            f"ratio={ratio:.4f} alerted_at={alerted_at}"
        )

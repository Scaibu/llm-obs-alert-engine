class ToxicityRules:
    RATE_LIMIT_TTL_SECONDS: int = 300
    SLACK_SAFETY_REVIEW_CHANNEL: str = "#llm-safety-review"

    @staticmethod
    def get_rate_limit_key(user_id: str, endpoint: str) -> str:
        return f"rate_limit:toxicity_alert:{user_id}:{endpoint}"

    @staticmethod
    def format_alert_message(
        span_id: str,
        user_id: str,
        endpoint: str,
        model: str,
        toxicity_score: float,
    ) -> str:
        return (
            f"Toxicity alert: high toxicity detected in response. "
            f"Span ID: {span_id}, User ID: {user_id}, Endpoint: {endpoint}, "
            f"Model: {model}, Toxicity Score: {toxicity_score:.4f}"
        )

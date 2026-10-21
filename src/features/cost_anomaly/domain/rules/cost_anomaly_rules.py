from datetime import datetime, timezone
from typing import Any

class CostAnomalyRules:
    COLD_START_THRESHOLD: int = 7
    BURN_RATIO_THRESHOLD: float = 3.0
    RATE_LIMIT_TTL_SECONDS: int = 3600
    SLACK_COST_ALERTS_CHANNEL: str = "#llm-cost-alerts"

    @staticmethod
    def is_cold_start(explicit_cold_start: bool | None, sample_count: int) -> bool:
        if explicit_cold_start is not None:
            return explicit_cold_start
        return sample_count < CostAnomalyRules.COLD_START_THRESHOLD

    @staticmethod
    def compute_burn_ratio(current_cost: float, ewma_value: float) -> float:
        return (current_cost / ewma_value) if ewma_value > 0.0 else 0.0

    @staticmethod
    def get_rate_limit_key(service: str, model: str) -> str:
        return f"rate_limit:cost_anomaly:{service}:{model}"

    @staticmethod
    def calculate_delivery_latency_ms(timestamp: str | None) -> int | None:
        if not timestamp:
            return None
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max(0, int((now - dt).total_seconds() * 1000))
        except Exception:
            return None

    @staticmethod
    def extract_top_cluster(cluster_drilldown: list[dict[str, Any]]) -> tuple[str, float]:
        if not cluster_drilldown:
            return "unknown", 0.0
        try:
            top_cluster = max(cluster_drilldown, key=lambda c: float(c.get("cost", 0.0)))
            return str(top_cluster.get("cluster_id", "unknown")), float(top_cluster.get("cost", 0.0))
        except Exception:
            return "unknown", 0.0

    @staticmethod
    def format_slack_message(
        service: str,
        model: str,
        current_cost: float,
        ewma_value: float,
        top_cluster_name: str,
        top_cluster_cost: float,
    ) -> str:
        return (
            f"Cost spike: {service}/{model} — ${current_cost:.4f} vs "
            f"${ewma_value:.4f} baseline. Likely cause: prompt cluster "
            f"'{top_cluster_name}' (${top_cluster_cost:.4f} of spike)"
        )

    @staticmethod
    def format_pagerduty_summary(service: str, model: str, burn_ratio: float) -> str:
        return f"Cost spike: {service}/{model} - burn ratio {burn_ratio:.2f}"

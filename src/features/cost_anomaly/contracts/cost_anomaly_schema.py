from typing import Any
from features.cost_anomaly.contracts.cost_anomaly_types import (
    CostAnomalyAlertPayload,
    CostAnomalyAlertResult,
    CostAnomalyValidationError,
)

class CostAnomalySchemaMapper:
    @staticmethod
    def from_api(data: dict[str, Any]) -> CostAnomalyAlertPayload:
        service = data.get("service")
        model = data.get("model")

        if not service or not isinstance(service, str):
            raise CostAnomalyValidationError("Missing or invalid service")
        if not model or not isinstance(model, str):
            raise CostAnomalyValidationError("Missing or invalid model")

        current_cost = data.get("current_cost", 0.0)
        ewma_value = data.get("ewma_value", 0.0)
        sample_count = data.get("sample_count", 0)

        if not isinstance(current_cost, (int, float)):
            raise TypeError("current_cost must be numeric")
        if not isinstance(ewma_value, (int, float)):
            raise TypeError("ewma_value must be numeric")
        if not isinstance(sample_count, int):
            raise TypeError("sample_count must be an integer")

        cluster_drilldown = data.get("cluster_drilldown")
        if not isinstance(cluster_drilldown, list):
            cluster_drilldown = []

        return CostAnomalyAlertPayload(
            service=service,
            model=model,
            sample_count=sample_count,
            current_cost=float(current_cost),
            ewma_value=float(ewma_value),
            timestamp=data.get("timestamp"),
            is_cold_start=data.get("is_cold_start"),
            cluster_drilldown=cluster_drilldown,
        )

    @staticmethod
    def to_api(result: CostAnomalyAlertResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "is_cold_start": result.is_cold_start,
            "burn_ratio": result.burn_ratio,
            "rate_limited": result.rate_limited,
            "delivery_latency_ms": result.delivery_latency_ms,
            "slack_message": result.slack_message,
            "pagerduty_summary": result.pagerduty_summary,
            "top_cluster_name": result.top_cluster_name,
            "top_cluster_cost": result.top_cluster_cost,
        }

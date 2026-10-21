from features.cost_anomaly.contracts.cost_anomaly_types import (
    CostAnomalyAlertPayload,
    CostAnomalyAlertResult,
)
from features.cost_anomaly.domain.rules.cost_anomaly_rules import CostAnomalyRules

class CostAnomalyWorkflow:
    @staticmethod
    def execute(payload: CostAnomalyAlertPayload, is_rate_limited: bool) -> CostAnomalyAlertResult:
        is_cold_start = CostAnomalyRules.is_cold_start(payload.is_cold_start, payload.sample_count)
        latency_ms = CostAnomalyRules.calculate_delivery_latency_ms(payload.timestamp)

        if is_cold_start:
            return CostAnomalyAlertResult(
                status="cold_start",
                is_cold_start=True,
                delivery_latency_ms=latency_ms,
            )

        burn_ratio = CostAnomalyRules.compute_burn_ratio(payload.current_cost, payload.ewma_value)

        if burn_ratio <= CostAnomalyRules.BURN_RATIO_THRESHOLD:
            return CostAnomalyAlertResult(
                status="suppressed",
                is_cold_start=False,
                burn_ratio=burn_ratio,
                delivery_latency_ms=latency_ms,
            )

        if is_rate_limited:
            return CostAnomalyAlertResult(
                status="rate_limited",
                is_cold_start=False,
                burn_ratio=burn_ratio,
                rate_limited=True,
                delivery_latency_ms=latency_ms,
            )

        top_cluster_name, top_cluster_cost = CostAnomalyRules.extract_top_cluster(
            payload.cluster_drilldown
        )
        slack_msg = CostAnomalyRules.format_slack_message(
            service=payload.service,
            model=payload.model,
            current_cost=payload.current_cost,
            ewma_value=payload.ewma_value,
            top_cluster_name=top_cluster_name,
            top_cluster_cost=top_cluster_cost,
        )
        pd_summary = CostAnomalyRules.format_pagerduty_summary(
            service=payload.service,
            model=payload.model,
            burn_ratio=burn_ratio,
        )

        return CostAnomalyAlertResult(
            status="triggered",
            is_cold_start=False,
            burn_ratio=burn_ratio,
            rate_limited=False,
            delivery_latency_ms=latency_ms,
            slack_message=slack_msg,
            pagerduty_summary=pd_summary,
            top_cluster_name=top_cluster_name,
            top_cluster_cost=top_cluster_cost,
        )

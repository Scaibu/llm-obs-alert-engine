from typing import Any
from opentelemetry import trace
from features.cost_anomaly.contracts.cost_anomaly_types import (
    CostAnomalyAlertPayload,
    CostAnomalyAlertResult,
)
from features.cost_anomaly.domain.rules.cost_anomaly_rules import CostAnomalyRules
from features.cost_anomaly.domain.workflows.cost_anomaly_workflow import CostAnomalyWorkflow
from features.cost_anomaly.infrastructure.ports.cost_anomaly_repository_port import CostAnomalyRepositoryPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort
from shared.utils.rate_limiter import check_and_acquire_rate_limit

tracer = trace.get_tracer("alert-engine")

class CostAnomalyService:
    def __init__(
        self,
        repository: CostAnomalyRepositoryPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        pagerduty_port: PagerDutyPort,
        metrics_port: MetricsPort,
    ) -> None:
        self._repository = repository
        self._redis_port = redis_port
        self._slack_port = slack_port
        self._pagerduty_port = pagerduty_port
        self._metrics_port = metrics_port

    def process_alert(
        self,
        payload: CostAnomalyAlertPayload,
        raw_payload: dict[str, Any],
    ) -> CostAnomalyAlertResult:
        with tracer.start_as_current_span(
            "cost_anomaly_service.process_alert",
            attributes={
                "alert.type": "cost_anomaly",
                "service": payload.service,
                "model": payload.model,
                "sample_count": payload.sample_count,
                "current_cost": payload.current_cost,
                "ewma_value": payload.ewma_value,
            },
        ) as span:
            is_cold = CostAnomalyRules.is_cold_start(payload.is_cold_start, payload.sample_count)
            delivery_latency_ms = CostAnomalyRules.calculate_delivery_latency_ms(payload.timestamp)

            if is_cold:
                span.set_attribute("alert.cold_start", True)
                with tracer.start_as_current_span("cost_anomaly_service.persist_cold_start"):
                    self._repository.record_alert(
                        alert_type="cost_anomaly",
                        service=payload.service,
                        model=payload.model,
                        user_id=None,
                        event_type="cold_start",
                        payload=raw_payload,
                        delivery_latency_ms=delivery_latency_ms,
                    )
                if delivery_latency_ms is not None:
                    self._metrics_port.record_delivery_latency(
                        alert_type="cost_anomaly",
                        severity="info",
                        latency_ms=float(delivery_latency_ms),
                    )
                return CostAnomalyWorkflow.execute(payload, is_rate_limited=False)

            burn_ratio = CostAnomalyRules.compute_burn_ratio(payload.current_cost, payload.ewma_value)
            span.set_attribute("alert.burn_ratio", burn_ratio)

            if burn_ratio <= CostAnomalyRules.BURN_RATIO_THRESHOLD:
                span.set_attribute("alert.suppressed", True)
                span.set_attribute("alert.suppression_reason", "burn_ratio_under_threshold")
                return CostAnomalyWorkflow.execute(payload, is_rate_limited=False)

            rate_limit_key = CostAnomalyRules.get_rate_limit_key(payload.service, payload.model)
            acquired = check_and_acquire_rate_limit(
                self._redis_port,
                rate_limit_key,
                CostAnomalyRules.RATE_LIMIT_TTL_SECONDS,
                "cost_anomaly_service.check_rate_limit"
            )
            if not acquired:
                span.set_attribute("alert.suppressed", True)
                return CostAnomalyWorkflow.execute(payload, is_rate_limited=True)

            result = CostAnomalyWorkflow.execute(payload, is_rate_limited=False)

            with tracer.start_as_current_span("cost_anomaly_service.persist_history"):
                self._repository.record_alert(
                    alert_type="cost_anomaly",
                    service=payload.service,
                    model=payload.model,
                    user_id=None,
                    event_type="spike",
                    payload=raw_payload,
                    delivery_latency_ms=result.delivery_latency_ms,
                )

            if result.delivery_latency_ms is not None:
                self._metrics_port.record_delivery_latency(
                    alert_type="cost_anomaly",
                    severity="critical",
                    latency_ms=float(result.delivery_latency_ms),
                )

            if result.slack_message:
                with tracer.start_as_current_span("cost_anomaly_service.notify_slack"):
                    self._slack_port.send_channel_message(
                        CostAnomalyRules.SLACK_COST_ALERTS_CHANNEL,
                        result.slack_message,
                    )

            if result.pagerduty_summary:
                with tracer.start_as_current_span("cost_anomaly_service.notify_pagerduty"):
                    self._pagerduty_port.trigger_incident(
                        summary=result.pagerduty_summary,
                        severity="critical",
                        source="alert-engine",
                        custom_details={
                            "service": payload.service,
                            "model": payload.model,
                            "current_cost": payload.current_cost,
                            "baseline_cost": payload.ewma_value,
                            "burn_ratio": result.burn_ratio,
                            "top_cluster": result.top_cluster_name,
                            "top_cluster_cost": result.top_cluster_cost,
                        },
                    )

            return result

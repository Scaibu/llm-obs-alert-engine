from typing import Any
from opentelemetry import trace
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort
from features.cost_anomaly.contracts.cost_anomaly_schema import CostAnomalySchemaMapper
from features.cost_anomaly.infrastructure.adapters.cost_anomaly_repository_adapter import CostAnomalyRepositoryAdapter
from features.cost_anomaly.service.cost_anomaly_service import CostAnomalyService

tracer = trace.get_tracer("alert-engine")

class CostAnomalyAlertHandler:
    def __init__(
        self,
        db_port: DbPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        pagerduty_port: PagerDutyPort,
        metrics_port: MetricsPort,
    ) -> None:
        self.db_port = db_port
        self.redis_port = redis_port
        self.slack_port = slack_port
        self.pagerduty_port = pagerduty_port
        self.metrics_port = metrics_port
        self._repository = CostAnomalyRepositoryAdapter(db_port)
        self._service = CostAnomalyService(
            repository=self._repository,
            redis_port=redis_port,
            slack_port=slack_port,
            pagerduty_port=pagerduty_port,
            metrics_port=metrics_port,
        )

    def handle(self, payload: dict[str, Any]) -> None:
        service = payload.get("service")
        model = payload.get("model")

        with tracer.start_as_current_span(
            "cost_anomaly_alert_handler.handle",
            attributes={
                "alert.type": "cost_anomaly",
                "service": service or "unknown",
                "model": model or "unknown",
            },
        ) as span:
            if not service or not model:
                span.set_status(trace.StatusCode.ERROR, "Missing required fields")
                return

            domain_payload = CostAnomalySchemaMapper.from_api(payload)
            self._service.process_alert(domain_payload, payload)

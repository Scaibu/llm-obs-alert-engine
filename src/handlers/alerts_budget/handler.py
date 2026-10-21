from typing import Any
from opentelemetry import trace
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.metrics_port import MetricsPort
from features.budget.contracts.budget_schema import BudgetSchemaMapper
from features.budget.infrastructure.adapters.budget_repository_adapter import BudgetRepositoryAdapter
from features.budget.service.budget_service import BudgetService

tracer = trace.get_tracer("alert-engine")

class BudgetAlertHandler:
    def __init__(
        self,
        db_port: DbPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        metrics_port: MetricsPort,
        service_owners_path: str,
    ) -> None:
        self.db_port = db_port
        self.redis_port = redis_port
        self.slack_port = slack_port
        self.metrics_port = metrics_port
        self.service_owners_path = service_owners_path
        self._repository = BudgetRepositoryAdapter(db_port)
        self._service = BudgetService(
            repository=self._repository,
            redis_port=redis_port,
            slack_port=slack_port,
            metrics_port=metrics_port,
            service_owners_path=service_owners_path,
        )

    def handle(self, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        model = payload.get("model")
        event_type = payload.get("event_type")

        with tracer.start_as_current_span(
            "budget_alert_handler.handle",
            attributes={
                "alert.type": "budget",
                "user_id": user_id or "unknown",
                "model": model or "unknown",
                "event_type": event_type or "unknown",
            },
        ) as span:
            if not user_id or not model or not event_type:
                span.set_status(trace.StatusCode.ERROR, "Missing required fields")
                return

            domain_payload = BudgetSchemaMapper.from_api(payload)
            self._service.process_alert(domain_payload, payload)

from typing import Any
from opentelemetry import trace
from features.budget.contracts.budget_types import BudgetAlertPayload, BudgetAlertResult
from features.budget.domain.rules.budget_rules import BudgetRules
from features.budget.domain.workflows.budget_workflow import BudgetWorkflow
from features.budget.infrastructure.ports.budget_repository_port import BudgetRepositoryPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.metrics_port import MetricsPort
from shared.utils.service_owners import load_service_owners
from shared.utils.rate_limiter import check_and_acquire_rate_limit

tracer = trace.get_tracer("alert-engine")

class BudgetService:
    def __init__(
        self,
        repository: BudgetRepositoryPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        metrics_port: MetricsPort,
        service_owners_path: str,
    ) -> None:
        self._repository = repository
        self._redis_port = redis_port
        self._slack_port = slack_port
        self._metrics_port = metrics_port
        self._service_owners_path = service_owners_path

    def _load_owners(self) -> dict[str, str]:
        return load_service_owners(self._service_owners_path)

    def process_alert(self, payload: BudgetAlertPayload, raw_payload: dict[str, Any]) -> BudgetAlertResult:
        rate_limit_key = BudgetRules.get_rate_limit_key(payload.user_id, payload.model)
        acquired = check_and_acquire_rate_limit(
            self._redis_port,
            rate_limit_key,
            BudgetRules.RATE_LIMIT_TTL_SECONDS,
            "budget_alert_handler.check_rate_limit",
        )
        if not acquired:
            return BudgetWorkflow.execute(payload, is_rate_limited=True)

        result = BudgetWorkflow.execute(payload, is_rate_limited=False)

        with tracer.start_as_current_span("budget_alert_handler.insert_database"):
            self._repository.record_alert(
                alert_type="budget",
                service=payload.service,
                model=payload.model,
                user_id=payload.user_id,
                event_type=payload.event_type,
                payload=raw_payload,
                delivery_latency_ms=result.delivery_latency_ms,
            )

        if result.severity == "critical":
            channel = BudgetRules.SLACK_COST_ALERTS_CHANNEL
            with tracer.start_as_current_span("budget_alert_handler.notify_slack_channel"):
                self._slack_port.send_channel_message(channel, result.message or "")

        elif result.severity == "warning":
            owners = self._load_owners()
            owner = owners.get(payload.service or "")
            if owner:
                with tracer.start_as_current_span("budget_alert_handler.notify_service_owner"):
                    self._slack_port.send_direct_message(
                        owner,
                        result.message or "",
                    )

        if result.delivery_latency_ms is not None:
            self._metrics_port.record_delivery_latency(
                alert_type="budget",
                severity=result.severity,
                latency_ms=float(result.delivery_latency_ms),
            )

        return result

"""
Blueprint:
- Pure domain orchestrator service for latency_ttft_regression alert lifecycle.
- Follows canonical role (06) service.
- Coordinates business rules, multi-step workflows, rate-limiting, notifications, and persistence.
- Emits structured child spans with trace attributes and records exceptions on error.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

import logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.metrics_port import MetricsPort
from shared.utils.rate_limiter import check_and_acquire_rate_limit
from features.latency_ttft_regression.contracts.latency_ttft_regression_types import (
    LatencyTtftRegressionAlertPayload,
)
from features.latency_ttft_regression.domain.rules.latency_ttft_regression_rules import (
    LatencyTtftRegressionRules,
)
from features.latency_ttft_regression.domain.workflows.latency_ttft_regression_workflow import (
    LatencyTtftRegressionWorkflow,
)
from features.latency_ttft_regression.infrastructure.adapters.latency_ttft_regression_repository_adapter import (
    LatencyTtftRegressionRepositoryAdapter,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")


class LatencyTtftRegressionService:
    def __init__(
        self,
        db_port: DbPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        metrics_port: MetricsPort,
    ) -> None:
        self.db_port = db_port
        self.redis_port = redis_port
        self.slack_port = slack_port
        self.metrics_port = metrics_port
        self.workflow = LatencyTtftRegressionWorkflow()
        self.repository = LatencyTtftRegressionRepositoryAdapter(db_port=db_port)

    def process_alert(self, payload: LatencyTtftRegressionAlertPayload) -> None:
        model = payload.model
        current = payload.current
        baseline = payload.baseline
        hour_of_day = payload.hour_of_day
        timestamp = payload.timestamp

        with tracer.start_as_current_span(
            "latency_ttft_regression_service.process_alert",
            attributes={
                "alert.type": LatencyTtftRegressionRules.ALERT_TYPE,
                "model": model,
                "current": current,
                "baseline": baseline,
                "hour_of_day": hour_of_day,
            },
        ) as span:
            try:
                delivery_latency_ms = self.workflow.calculate_delivery_latency(timestamp)
                rate_limit_key = LatencyTtftRegressionRules.get_rate_limit_key(
                    model, hour_of_day
                )

                acquired = check_and_acquire_rate_limit(
                    self.redis_port,
                    rate_limit_key,
                    LatencyTtftRegressionRules.RATE_LIMIT_TTL_SECONDS,
                    "latency_ttft_regression_service.check_rate_limit"
                )
                if not acquired:
                    span.set_attribute("alert.suppressed", True)
                    logger.info(
                        "Latency TTFT regression alert suppressed for model=%s hour_of_day=%s due to rate limit",
                        model,
                        hour_of_day,
                    )
                    return

                with tracer.start_as_current_span(
                    "latency_ttft_regression_service.insert_database"
                ):
                    record = self.workflow.prepare_database_record(
                        payload, delivery_latency_ms
                    )
                    self.repository.save_alert(record)

                slack_msg = self.workflow.prepare_slack_message(payload)
                with tracer.start_as_current_span(
                    "latency_ttft_regression_service.notify_slack"
                ):
                    self.slack_port.send_channel_message(
                        LatencyTtftRegressionRules.SLACK_ALERTS_CHANNEL, slack_msg
                    )
                logger.info(
                    "Slack alert sent to %s for TTFT regression on %s",
                    LatencyTtftRegressionRules.SLACK_ALERTS_CHANNEL,
                    model,
                )

                if delivery_latency_ms is not None:
                    try:
                        self.metrics_port.record_delivery_latency(
                            alert_type=LatencyTtftRegressionRules.ALERT_TYPE,
                            severity=LatencyTtftRegressionRules.EVENT_TYPE,
                            latency_ms=float(delivery_latency_ms),
                        )
                    except Exception:
                        pass

                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise

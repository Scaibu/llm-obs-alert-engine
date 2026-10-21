"""
Blueprint:
- Pure domain orchestrator service for latency_slo alert lifecycle.
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
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort
from features.latency_slo.contracts.latency_slo_types import LatencySloAlertPayload
from features.latency_slo.domain.rules.latency_slo_rules import LatencySloRules
from features.latency_slo.domain.workflows.latency_slo_workflow import (
    LatencySloWorkflow,
)
from features.latency_slo.infrastructure.adapters.latency_slo_repository_adapter import (
    LatencySloRepositoryAdapter,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")


class LatencySloService:
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
        self.workflow = LatencySloWorkflow()
        self.repository = LatencySloRepositoryAdapter(db_port=db_port)

    def process_alert(self, payload: LatencySloAlertPayload) -> None:
        model = payload.model
        endpoint = payload.endpoint
        severity = payload.severity
        burn_rate = payload.burn_rate
        p95_current = payload.p95_current
        p95_baseline = payload.p95_baseline
        p99_current = payload.p99_current
        p99_baseline = payload.p99_baseline
        budget_remaining = payload.budget_remaining
        timestamp = payload.timestamp

        with tracer.start_as_current_span(
            "latency_slo_service.process_alert",
            attributes={
                "alert.type": "latency_slo",
                "model": model,
                "endpoint": endpoint,
                "severity": severity,
                "burn_rate": burn_rate,
                "budget_remaining": budget_remaining,
            },
        ) as span:
            try:
                delivery_latency_ms = self.workflow.calculate_delivery_latency(timestamp)
                route = self.workflow.evaluate_route(severity)

                if route == "page":
                    rate_limit_key = LatencySloRules.get_page_rate_limit_key(model, endpoint)
                    with tracer.start_as_current_span(
                        "latency_slo_service.check_rate_limit"
                    ) as sub_span:
                        sub_span.set_attribute("rate_limit.key", rate_limit_key)
                        acquired = self.redis_port.acquire_rate_limit(
                            rate_limit_key, LatencySloRules.RATE_LIMIT_PAGE_TTL_SECONDS
                        )
                        sub_span.set_attribute("rate_limit.acquired", acquired)
                        if not acquired:
                            span.set_attribute("alert.suppressed", True)
                            logger.info(
                                "Latency SLO page alert suppressed for model=%s endpoint=%s due to rate limit",
                                model,
                                endpoint,
                            )
                            return

                    title, custom_details = self.workflow.prepare_pagerduty_payload(payload)
                    with tracer.start_as_current_span(
                        "latency_slo_service.notify_pagerduty"
                    ):
                        incident_id = self.pagerduty_port.trigger_incident(
                            summary=title,
                            severity="critical",
                            source=LatencySloRules.SOURCE_ALERT_ENGINE,
                            custom_details=custom_details,
                        )
                        if incident_id:
                            self.redis_port.set_open_incident(
                                model,
                                endpoint,
                                incident_id,
                                LatencySloRules.INCIDENT_TTL_SECONDS,
                            )
                    logger.info(
                        "PagerDuty alert triggered: %s, tracked incident_id: %s",
                        title,
                        incident_id,
                    )

                elif route == "resolve":
                    with tracer.start_as_current_span(
                        "latency_slo_service.auto_resolve"
                    ):
                        incident_id = self.redis_port.get_open_incident(model, endpoint)
                        if incident_id:
                            self.pagerduty_port.resolve_incident(incident_id)
                            self.redis_port.delete_open_incident(model, endpoint)
                            slack_msg = self.workflow.prepare_slack_resolve_message(
                                model, endpoint
                            )
                            self.slack_port.send_channel_message(
                                LatencySloRules.SLACK_ALERTS_CHANNEL, slack_msg
                            )
                            logger.info(
                                "PagerDuty incident %s resolved automatically for model=%s endpoint=%s",
                                incident_id,
                                model,
                                endpoint,
                            )

                elif route == "slack":
                    slack_msg = self.workflow.prepare_slack_breach_message(payload)
                    with tracer.start_as_current_span(
                        "latency_slo_service.notify_slack"
                    ):
                        self.slack_port.send_channel_message(
                            LatencySloRules.SLACK_ALERTS_CHANNEL, slack_msg
                        )
                    logger.info(
                        "Slack alert sent to %s for %s/%s",
                        LatencySloRules.SLACK_ALERTS_CHANNEL,
                        model,
                        endpoint,
                    )

                elif route == "ticket":
                    with tracer.start_as_current_span(
                        "latency_slo_service.insert_database"
                    ):
                        record = self.workflow.prepare_database_record(
                            payload, delivery_latency_ms
                        )
                        self.repository.save_alert(record)
                    logger.info(
                        "Latency SLO ticket alert logged to alert_history for model=%s endpoint=%s",
                        model,
                        endpoint,
                    )

                if delivery_latency_ms is not None:
                    try:
                        self.metrics_port.record_delivery_latency(
                            alert_type="latency_slo",
                            severity=severity,
                            latency_ms=float(delivery_latency_ms),
                        )
                    except Exception:
                        pass

                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise

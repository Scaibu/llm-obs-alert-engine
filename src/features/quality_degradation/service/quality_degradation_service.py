import logging
from typing import Any
from opentelemetry import trace
from features.quality_degradation.contracts.quality_degradation_types import (
    QualityDegradationPayload,
    QualityDegradationResult,
)
from features.quality_degradation.domain.rules.quality_degradation_rules import QualityDegradationRules
from features.quality_degradation.domain.workflows.quality_degradation_workflow import QualityDegradationWorkflow
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from shared.utils.rate_limiter import check_and_acquire_rate_limit

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class QualityDegradationService:
    def __init__(
        self,
        redis_port: RedisPort,
        slack_port: SlackPort,
    ) -> None:
        self._redis_port = redis_port
        self._slack_port = slack_port

    def process_alert(self, payload: QualityDegradationPayload) -> QualityDegradationResult:
        with tracer.start_as_current_span(
            "quality_degradation_service.process_alert",
            attributes={
                "alert.type": "quality_degradation",
                "model": payload.model,
                "endpoint": payload.endpoint,
                "is_cold_start": payload.is_cold_start,
            },
        ) as span:
            if payload.is_cold_start:
                logger.warning(
                    "quality_degradation_service: cold-start suppressed alert "
                    "model=%s endpoint=%s current_avg=%.4f baseline=%.4f ratio=%.4f",
                    payload.model, payload.endpoint, payload.current_window_avg, payload.baseline, payload.ratio,
                )
                span.set_attribute("alert.cold_start_suppressed", True)
                return QualityDegradationWorkflow.execute(payload, is_rate_limited=False)

            rate_limit_key = QualityDegradationRules.get_rate_limit_key(payload.model, payload.endpoint)
            acquired = check_and_acquire_rate_limit(
                self._redis_port,
                rate_limit_key,
                QualityDegradationRules.RATE_LIMIT_TTL_SECONDS,
                "quality_degradation_service.check_rate_limit"
            )
            if not acquired:
                span.set_attribute("alert.suppressed", True)
                return QualityDegradationWorkflow.execute(payload, is_rate_limited=True)

            result = QualityDegradationWorkflow.execute(payload, is_rate_limited=False)

            if result.message:
                with tracer.start_as_current_span("quality_degradation_service.notify_slack"):
                    self._slack_port.send_channel_message(
                        QualityDegradationRules.SLACK_QUALITY_ALERTS_CHANNEL,
                        result.message,
                    )

            return result

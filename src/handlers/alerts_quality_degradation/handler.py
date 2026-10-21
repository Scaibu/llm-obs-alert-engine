from __future__ import annotations

import logging
from typing import Any
from opentelemetry import trace
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from features.quality_degradation.contracts.quality_degradation_schema import QualityDegradationSchemaMapper
from features.quality_degradation.service.quality_degradation_service import QualityDegradationService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class QualityDegradationAlertHandler:
    def __init__(
        self,
        redis_port: RedisPort,
        slack_port: SlackPort,
    ) -> None:
        self.redis_port = redis_port
        self.slack_port = slack_port
        self._service = QualityDegradationService(
            redis_port=redis_port,
            slack_port=slack_port,
        )

    def handle(self, payload: dict[str, Any]) -> None:
        model = payload.get("model")
        endpoint = payload.get("endpoint")
        current_window_avg = payload.get("current_window_avg")
        baseline = payload.get("baseline")
        ratio = payload.get("ratio")
        alerted_at = payload.get("alerted_at")
        is_cold_start: bool = bool(payload.get("is_cold_start", False))

        with tracer.start_as_current_span(
            "quality_degradation_alert_handler.handle",
            attributes={
                "alert.type": "quality_degradation",
                "model": model or "unknown",
                "endpoint": endpoint or "unknown",
                "is_cold_start": is_cold_start,
            },
        ) as span:
            if (
                model is None
                or endpoint is None
                or current_window_avg is None
                or baseline is None
                or ratio is None
                or alerted_at is None
            ):
                span.set_status(trace.StatusCode.ERROR, "Missing required fields")
                logger.warning(
                    "quality_degradation_handler: missing required fields in payload=%s",
                    payload,
                )
                return

            domain_payload = QualityDegradationSchemaMapper.from_api(payload)
            self._service.process_alert(domain_payload)

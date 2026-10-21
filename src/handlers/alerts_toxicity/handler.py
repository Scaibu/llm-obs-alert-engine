from __future__ import annotations

import logging
from typing import Any
from opentelemetry import trace
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from features.toxicity.contracts.toxicity_schema import ToxicitySchemaMapper
from features.toxicity.service.toxicity_service import ToxicityService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("alert-engine")

class ToxicityAlertHandler:
    def __init__(
        self,
        redis_port: RedisPort,
        slack_port: SlackPort,
    ) -> None:
        self.redis_port = redis_port
        self.slack_port = slack_port
        self._service = ToxicityService(
            redis_port=redis_port,
            slack_port=slack_port,
        )

    def handle(self, payload: dict[str, Any]) -> None:
        span_id = payload.get("span_id")
        toxicity_score = payload.get("toxicity_score")
        user_id = payload.get("user_id") or "unknown"
        endpoint = payload.get("endpoint") or "unknown"

        with tracer.start_as_current_span(
            "toxicity_alert_handler.handle",
            attributes={
                "alert.type": "toxicity",
                "span_id": span_id or "unknown",
                "user_id": user_id,
                "endpoint": endpoint,
            },
        ) as span:
            if not span_id or toxicity_score is None:
                span.set_status(trace.StatusCode.ERROR, "Missing required fields")
                return

            domain_payload = ToxicitySchemaMapper.from_api(payload)
            self._service.process_alert(domain_payload)

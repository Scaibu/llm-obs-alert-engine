from typing import Any
from opentelemetry import trace
from features.toxicity.contracts.toxicity_types import (
    ToxicityPayload,
    ToxicityResult,
)
from features.toxicity.domain.rules.toxicity_rules import ToxicityRules
from features.toxicity.domain.workflows.toxicity_workflow import ToxicityWorkflow
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from shared.utils.rate_limiter import check_and_acquire_rate_limit

tracer = trace.get_tracer("alert-engine")

class ToxicityService:
    def __init__(
        self,
        redis_port: RedisPort,
        slack_port: SlackPort,
    ) -> None:
        self._redis_port = redis_port
        self._slack_port = slack_port

    def process_alert(self, payload: ToxicityPayload) -> ToxicityResult:
        with tracer.start_as_current_span(
            "toxicity_service.process_alert",
            attributes={
                "alert.type": "toxicity",
                "span_id": payload.span_id,
                "user_id": payload.user_id,
                "endpoint": payload.endpoint,
            },
        ) as span:
            rate_limit_key = ToxicityRules.get_rate_limit_key(payload.user_id, payload.endpoint)
            acquired = check_and_acquire_rate_limit(
                self._redis_port,
                rate_limit_key,
                ToxicityRules.RATE_LIMIT_TTL_SECONDS,
                "toxicity_service.check_rate_limit"
            )
            if not acquired:
                span.set_attribute("alert.suppressed", True)
                return ToxicityWorkflow.execute(payload, is_rate_limited=True)

            result = ToxicityWorkflow.execute(payload, is_rate_limited=False)

            if result.message:
                with tracer.start_as_current_span("toxicity_service.notify_slack"):
                    self._slack_port.send_channel_message(
                        ToxicityRules.SLACK_SAFETY_REVIEW_CHANNEL,
                        result.message,
                    )

            return result

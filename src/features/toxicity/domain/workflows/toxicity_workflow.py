from features.toxicity.contracts.toxicity_types import (
    ToxicityPayload,
    ToxicityResult,
)
from features.toxicity.domain.rules.toxicity_rules import ToxicityRules

class ToxicityWorkflow:
    @staticmethod
    def execute(payload: ToxicityPayload, is_rate_limited: bool) -> ToxicityResult:
        if is_rate_limited:
            return ToxicityResult(status="rate_limited", rate_limited=True)

        msg = ToxicityRules.format_alert_message(
            span_id=payload.span_id,
            user_id=payload.user_id,
            endpoint=payload.endpoint,
            model=payload.model,
            toxicity_score=payload.toxicity_score,
        )

        return ToxicityResult(status="triggered", rate_limited=False, message=msg)

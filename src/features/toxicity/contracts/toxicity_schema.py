from typing import Any
from features.toxicity.contracts.toxicity_types import (
    ToxicityPayload,
    ToxicityResult,
    ToxicityValidationError,
)

class ToxicitySchemaMapper:
    @staticmethod
    def from_api(data: dict[str, Any]) -> ToxicityPayload:
        span_id = data.get("span_id")
        toxicity_score = data.get("toxicity_score")

        if not span_id or toxicity_score is None:
            raise ToxicityValidationError("Missing required span_id or toxicity_score")

        return ToxicityPayload(
            span_id=str(span_id),
            toxicity_score=float(toxicity_score),
            user_id=str(data.get("user_id") or "unknown"),
            endpoint=str(data.get("endpoint") or "unknown"),
            model=str(data.get("model") or "unknown"),
        )

    @staticmethod
    def to_api(result: ToxicityResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "rate_limited": result.rate_limited,
            "message": result.message,
        }

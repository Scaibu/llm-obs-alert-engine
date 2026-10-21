from dataclasses import dataclass

@dataclass(frozen=True)
class ToxicityPayload:
    span_id: str
    toxicity_score: float
    user_id: str = "unknown"
    endpoint: str = "unknown"
    model: str = "unknown"

@dataclass(frozen=True)
class ToxicityResult:
    status: str
    rate_limited: bool = False
    message: str | None = None

class ToxicityValidationError(Exception):
    pass

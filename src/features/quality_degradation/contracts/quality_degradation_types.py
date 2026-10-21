from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class QualityDegradationPayload:
    model: str
    endpoint: str
    current_window_avg: float
    baseline: float
    ratio: float
    alerted_at: str
    is_cold_start: bool = False

@dataclass(frozen=True)
class QualityDegradationResult:
    status: str
    rate_limited: bool = False
    cold_start_suppressed: bool = False
    message: str | None = None

class QualityDegradationValidationError(Exception):
    pass

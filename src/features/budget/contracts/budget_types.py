from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class BudgetAlertPayload:
    user_id: str
    model: str
    event_type: str
    service: str | None = None
    timestamp_utc: str | None = None

@dataclass(frozen=True)
class BudgetAlertResult:
    status: str
    rate_limited: bool = False
    message: str | None = None
    severity: str = "warning"
    delivery_latency_ms: int | None = None

class BudgetValidationError(Exception):
    pass

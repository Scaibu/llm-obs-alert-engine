from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CostAnomalyAlertPayload:
    service: str
    model: str
    sample_count: int = 0
    current_cost: float = 0.0
    ewma_value: float = 0.0
    timestamp: str | None = None
    is_cold_start: bool | None = None
    cluster_drilldown: list[dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class CostAnomalyAlertResult:
    status: str
    is_cold_start: bool = False
    burn_ratio: float = 0.0
    rate_limited: bool = False
    delivery_latency_ms: int | None = None
    slack_message: str | None = None
    pagerduty_summary: str | None = None
    top_cluster_name: str = "unknown"
    top_cluster_cost: float = 0.0

class CostAnomalyValidationError(Exception):
    pass

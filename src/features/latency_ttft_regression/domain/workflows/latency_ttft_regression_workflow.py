"""
Blueprint:
- Multi-step DAG workflow for processing latency TTFT regression alerts.
- Follows canonical role (09) workflow.
- Coordinates rate-limit checking, payload formatting, database record preparation, and message synthesis.
- 100% comment-free function and class bodies per rule (6).
"""

from __future__ import annotations

from typing import Optional
from features.latency_ttft_regression.contracts.latency_ttft_regression_types import (
    LatencyTtftRegressionAlertPayload,
    LatencyTtftRegressionRecord,
)
from features.latency_ttft_regression.domain.rules.latency_ttft_regression_rules import (
    LatencyTtftRegressionRules,
)


class LatencyTtftRegressionWorkflow:
    def calculate_delivery_latency(self, timestamp: Optional[str]) -> Optional[int]:
        return LatencyTtftRegressionRules.compute_delivery_latency_ms(timestamp)

    def prepare_slack_message(
        self, payload: LatencyTtftRegressionAlertPayload
    ) -> str:
        return LatencyTtftRegressionRules.format_slack_message(payload)

    def prepare_database_record(
        self,
        payload: LatencyTtftRegressionAlertPayload,
        delivery_latency_ms: Optional[int],
    ) -> LatencyTtftRegressionRecord:
        db_payload = LatencyTtftRegressionRules.format_database_payload(payload)
        return LatencyTtftRegressionRecord(
            alert_type=LatencyTtftRegressionRules.ALERT_TYPE,
            service=None,
            model=payload.model,
            user_id=None,
            event_type=LatencyTtftRegressionRules.EVENT_TYPE,
            payload=db_payload,
            delivery_latency_ms=delivery_latency_ms,
        )

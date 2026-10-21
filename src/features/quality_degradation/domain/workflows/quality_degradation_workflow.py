from features.quality_degradation.contracts.quality_degradation_types import (
    QualityDegradationPayload,
    QualityDegradationResult,
)
from features.quality_degradation.domain.rules.quality_degradation_rules import QualityDegradationRules

class QualityDegradationWorkflow:
    @staticmethod
    def execute(payload: QualityDegradationPayload, is_rate_limited: bool) -> QualityDegradationResult:
        if payload.is_cold_start:
            return QualityDegradationResult(
                status="cold_start_suppressed",
                cold_start_suppressed=True,
            )

        if is_rate_limited:
            return QualityDegradationResult(
                status="rate_limited",
                rate_limited=True,
            )

        msg = QualityDegradationRules.format_alert_message(
            model=payload.model,
            endpoint=payload.endpoint,
            current_window_avg=payload.current_window_avg,
            baseline=payload.baseline,
            ratio=payload.ratio,
            alerted_at=payload.alerted_at,
        )

        return QualityDegradationResult(
            status="triggered",
            rate_limited=False,
            cold_start_suppressed=False,
            message=msg,
        )

from typing import Any
from features.quality_degradation.contracts.quality_degradation_types import (
    QualityDegradationPayload,
    QualityDegradationResult,
    QualityDegradationValidationError,
)

class QualityDegradationSchemaMapper:
    @staticmethod
    def from_api(data: dict[str, Any]) -> QualityDegradationPayload:
        model = data.get("model")
        endpoint = data.get("endpoint")
        current_window_avg = data.get("current_window_avg")
        baseline = data.get("baseline")
        ratio = data.get("ratio")
        alerted_at = data.get("alerted_at")

        if (
            model is None
            or endpoint is None
            or current_window_avg is None
            or baseline is None
            or ratio is None
            or alerted_at is None
        ):
            raise QualityDegradationValidationError("Missing required fields for quality degradation")

        return QualityDegradationPayload(
            model=str(model),
            endpoint=str(endpoint),
            current_window_avg=float(current_window_avg),
            baseline=float(baseline),
            ratio=float(ratio),
            alerted_at=str(alerted_at),
            is_cold_start=bool(data.get("is_cold_start", False)),
        )

    @staticmethod
    def to_api(result: QualityDegradationResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "rate_limited": result.rate_limited,
            "cold_start_suppressed": result.cold_start_suppressed,
            "message": result.message,
        }

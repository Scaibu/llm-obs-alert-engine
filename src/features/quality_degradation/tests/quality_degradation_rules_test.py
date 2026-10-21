import pytest
from features.quality_degradation.domain.rules.quality_degradation_rules import QualityDegradationRules

def test_quality_degradation_rate_limit_key() -> None:
    key = QualityDegradationRules.get_rate_limit_key("gpt-4", "/chat/completions")
    assert key == "rate_limit:quality_degradation:gpt-4:/chat/completions"

def test_quality_degradation_format_message() -> None:
    msg = QualityDegradationRules.format_alert_message(
        model="gpt-4",
        endpoint="/chat/completions",
        current_window_avg=0.65,
        baseline=0.90,
        ratio=0.7222,
        alerted_at="2026-05-28T12:00:00Z",
    )
    assert "model=gpt-4" in msg
    assert "endpoint=/chat/completions" in msg

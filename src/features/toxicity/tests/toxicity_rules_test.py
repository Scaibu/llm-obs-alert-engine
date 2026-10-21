import pytest
from features.toxicity.domain.rules.toxicity_rules import ToxicityRules

def test_toxicity_rate_limit_key() -> None:
    key = ToxicityRules.get_rate_limit_key("usr-123", "/chat")
    assert key == "rate_limit:toxicity_alert:usr-123:/chat"

def test_toxicity_format_message() -> None:
    msg = ToxicityRules.format_alert_message(
        span_id="sp-1",
        user_id="usr-1",
        endpoint="/chat",
        model="gpt-4",
        toxicity_score=0.95,
    )
    assert "Span ID: sp-1" in msg
    assert "Toxicity Score: 0.9500" in msg

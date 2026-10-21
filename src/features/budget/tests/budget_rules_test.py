import pytest
from features.budget.domain.rules.budget_rules import BudgetRules

def test_budget_rate_limit_key() -> None:
    key = BudgetRules.get_rate_limit_key("usr-123", "gpt-4")
    assert key == "rate_limit:budget_alert:usr-123:gpt-4"

def test_budget_format_blocked() -> None:
    msg = BudgetRules.format_alert_message("usr-123", "gpt-4", "blocked")
    assert "blocked for model" in msg

def test_budget_format_warning() -> None:
    msg = BudgetRules.format_alert_message("usr-123", "gpt-4", "warning_80pct")
    assert "consumed 80% of budget" in msg

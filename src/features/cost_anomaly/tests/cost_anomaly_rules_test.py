import pytest
from features.cost_anomaly.domain.rules.cost_anomaly_rules import CostAnomalyRules

def test_cost_anomaly_cold_start() -> None:
    assert CostAnomalyRules.is_cold_start(None, 5) is True
    assert CostAnomalyRules.is_cold_start(None, 10) is False
    assert CostAnomalyRules.is_cold_start(True, 20) is True

def test_cost_anomaly_burn_ratio() -> None:
    ratio = CostAnomalyRules.compute_burn_ratio(10.0, 2.0)
    assert ratio == 5.0
    assert CostAnomalyRules.compute_burn_ratio(10.0, 0.0) == 0.0

def test_cost_anomaly_rate_limit_key() -> None:
    key = CostAnomalyRules.get_rate_limit_key("billing", "gpt-4")
    assert key == "rate_limit:cost_anomaly:billing:gpt-4"

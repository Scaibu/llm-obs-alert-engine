from unittest.mock import MagicMock
from handlers.alerts_budget.handler import BudgetAlertHandler
from handlers.alerts_cost_anomaly.handler import CostAnomalyAlertHandler
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort

def test_scenario_budget_exhaustion_and_owner_dispatch() -> None:
    db = MagicMock(spec=DbPort)
    redis = MagicMock(spec=RedisPort)
    redis.acquire_rate_limit.return_value = True
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    budget_handler = BudgetAlertHandler(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        metrics_port=metrics,
        service_owners_path="config/service_owners.yaml",
    )

    cost_handler = CostAnomalyAlertHandler(
        db_port=db,
        redis_port=redis,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
    )

    budget_handler.handle({
        "user_id": "usr-billing-dev",
        "service": "billing_service",
        "model": "gpt-4",
        "event_type": "threshold_warning",
        "current_spend": 850.0,
        "budget_limit": 1000.0,
    })

    assert slack.send_direct_message.call_count == 1
    call_args = slack.send_direct_message.call_args[0]
    assert call_args[0] == "@john-billing"
    assert db.insert_alert.call_count == 1

    budget_handler.handle({
        "user_id": "usr-billing-dev",
        "service": "billing_service",
        "model": "gpt-4",
        "event_type": "blocked",
        "current_spend": 1020.0,
        "budget_limit": 1000.0,
    })

    assert slack.send_channel_message.call_count == 1
    assert db.insert_alert.call_count == 2

    cost_handler.handle({
        "service": "billing_service",
        "model": "gpt-4",
        "current_cost": 450.0,
        "ewma_value": 35.0,
        "sample_count": 50,
    })

    assert pd.trigger_incident.call_count == 1
    pd_args = pd.trigger_incident.call_args[1]
    assert pd_args["severity"] == "critical"
    assert pd_args["custom_details"]["service"] == "billing_service"
    assert db.insert_alert.call_count == 3

from unittest.mock import MagicMock
from handlers.alerts_latency_slo.handler import LatencySloAlertHandler
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort

class MockRedisIncidentStore:
    def __init__(self) -> None:
        self.incidents: dict[str, str] = {}
        self.rate_limits: set[str] = set()

    def acquire_rate_limit(self, key: str, ttl_seconds: int) -> bool:
        if key in self.rate_limits:
            return False
        self.rate_limits.add(key)
        return True

    def get_open_incident(self, model: str, endpoint: str) -> str | None:
        return self.incidents.get(f"{model}:{endpoint}")

    def set_open_incident(self, model: str, endpoint: str, incident_id: str, ttl: int) -> None:
        self.incidents[f"{model}:{endpoint}"] = incident_id

    def delete_open_incident(self, model: str, endpoint: str) -> None:
        self.incidents.pop(f"{model}:{endpoint}", None)

def test_scenario_latency_slo_incident_lifecycle() -> None:
    db = MagicMock(spec=DbPort)
    redis_store = MockRedisIncidentStore()
    slack = MagicMock(spec=SlackPort)
    pd = MagicMock(spec=PagerDutyPort)
    metrics = MagicMock(spec=MetricsPort)

    pd.trigger_incident.return_value = "pd_inc_4567"

    handler = LatencySloAlertHandler(
        db_port=db,
        redis_port=redis_store,
        slack_port=slack,
        pagerduty_port=pd,
        metrics_port=metrics,
    )

    breach_event = {
        "model": "gpt-4",
        "endpoint": "/v1/chat",
        "severity": "page",
        "burn_rate": 2.5,
        "p95_current": 120.0,
        "p95_baseline": 50.0,
        "p99_current": 250.0,
        "p99_baseline": 100.0,
        "budget_remaining": 88.5,
        "timestamp": "2026-06-29T09:00:00Z",
    }

    handler.handle(breach_event)

    assert pd.trigger_incident.call_count == 1
    assert redis_store.get_open_incident("gpt-4", "/v1/chat") == "pd_inc_4567"

    follow_up_breach = {
        "model": "gpt-4",
        "endpoint": "/v1/chat",
        "severity": "page",
        "burn_rate": 2.8,
        "p95_current": 130.0,
        "p95_baseline": 50.0,
        "p99_current": 270.0,
        "p99_baseline": 100.0,
        "budget_remaining": 85.0,
        "timestamp": "2026-06-29T09:05:00Z",
    }

    handler.handle(follow_up_breach)
    assert pd.trigger_incident.call_count == 1

    resolve_event = {
        "model": "gpt-4",
        "endpoint": "/v1/chat",
        "severity": "None",
        "burn_rate": 0.5,
        "p95_current": 45.0,
        "p95_baseline": 50.0,
        "p99_current": 90.0,
        "p99_baseline": 100.0,
        "budget_remaining": 98.0,
        "timestamp": "2026-06-29T09:10:00Z",
    }

    handler.handle(resolve_event)

    pd.resolve_incident.assert_called_once_with("pd_inc_4567")
    assert redis_store.get_open_incident("gpt-4", "/v1/chat") is None
    assert slack.send_channel_message.call_count == 1
    assert "resolved" in slack.send_channel_message.call_args[0][1].lower()

    redis_store.rate_limits.clear()

    fresh_breach = {
        "model": "gpt-4",
        "endpoint": "/v1/chat",
        "severity": "page",
        "burn_rate": 3.0,
        "p95_current": 150.0,
        "p95_baseline": 50.0,
        "p99_current": 300.0,
        "p99_baseline": 100.0,
        "budget_remaining": 80.0,
        "timestamp": "2026-06-29T09:15:00Z",
    }

    handler.handle(fresh_breach)

    assert pd.trigger_incident.call_count == 2
    assert redis_store.get_open_incident("gpt-4", "/v1/chat") == "pd_inc_4567"

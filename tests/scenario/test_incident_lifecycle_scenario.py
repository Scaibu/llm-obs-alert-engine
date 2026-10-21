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
        "model": "gpt-4-turbo",
        "endpoint": "/v1/chat/completions",
        "slo_target_ms": 800.0,
        "current_p95_ms": 2400.0,
        "sample_count": 100,
    }

    handler.handle(breach_event)

    assert pd.trigger_incident.call_count == 1
    assert slack.send_channel_message.call_count == 1
    assert db.insert_alert.call_count == 1
    assert redis_store.get_open_incident("gpt-4-turbo", "/v1/chat/completions") == "pd_inc_4567"

    follow_up_breach = {
        "model": "gpt-4-turbo",
        "endpoint": "/v1/chat/completions",
        "slo_target_ms": 800.0,
        "current_p95_ms": 2600.0,
        "sample_count": 120,
    }

    handler.handle(follow_up_breach)

    assert pd.trigger_incident.call_count == 1
    assert db.insert_alert.call_count == 2

    redis_store.delete_open_incident("gpt-4-turbo", "/v1/chat/completions")
    redis_store.rate_limits.clear()

    fresh_breach = {
        "model": "gpt-4-turbo",
        "endpoint": "/v1/chat/completions",
        "slo_target_ms": 800.0,
        "current_p95_ms": 3100.0,
        "sample_count": 80,
    }

    handler.handle(fresh_breach)

    assert pd.trigger_incident.call_count == 2
    assert db.insert_alert.call_count == 3

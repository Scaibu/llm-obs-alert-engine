import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from psycopg.errors import IntegrityError

from adapters.postgres.postgres_adapter import PostgresAdapter
from adapters.redis.redis_adapter import RedisAdapter
from adapters.slack.slack_adapter import SlackAdapter
from adapters.pagerduty.pagerduty_adapter import PagerDutyAdapter
from adapters.metrics.prometheus_adapter import PrometheusAdapter
from shared.errors.application_error import ValidationError

class FakeIntegrityError(IntegrityError):
    def __init__(self, msg: str, constraint_name: str) -> None:
        super().__init__(msg)
        diag = MagicMock()
        diag.constraint_name = constraint_name
        self.diag = diag

def test_postgres_adapter_insert_alert_success() -> None:
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        adapter = PostgresAdapter("postgresql://user:pass@localhost:5432/db")
        adapter.insert_alert(
            alert_type="budget",
            service="billing",
            model="gpt-4",
            user_id="usr-123",
            event_type="threshold_exceeded",
            payload={"threshold": 0.85},
            delivery_latency_ms=120,
        )

    mock_cursor.execute.assert_called_once()
    args, _ = mock_cursor.execute.call_args
    assert "INSERT INTO alert_history" in args[0]
    params = args[1]
    assert params[0] == "budget"
    assert params[1] == "billing"
    assert params[2] == "gpt-4"
    assert params[3] == "usr-123"
    assert params[4] == "threshold_exceeded"
    assert json.loads(params[5]) == {"threshold": 0.85}
    assert params[6] == 120
    mock_conn.commit.assert_called_once()

def test_postgres_adapter_constraint_error_mapping() -> None:
    exc = FakeIntegrityError("check constraint violation", "alert_history_alert_type_ck")
    mock_conn = MagicMock()
    mock_conn.__enter__.side_effect = exc

    with patch("psycopg.connect", return_value=mock_conn):
        adapter = PostgresAdapter("postgresql://user:pass@localhost:5432/db")
        with pytest.raises(ValidationError):
            adapter.insert_alert(
                alert_type="invalid_type",
                service=None,
                model=None,
                user_id=None,
                event_type=None,
                payload={},
                delivery_latency_ms=None,
            )

def test_postgres_adapter_generic_exception_propagation() -> None:
    with patch("psycopg.connect", side_effect=RuntimeError("connection pool exhausted")):
        adapter = PostgresAdapter("postgresql://user:pass@localhost:5432/db")
        with pytest.raises(RuntimeError, match="connection pool exhausted"):
            adapter.insert_alert(
                alert_type="budget",
                service=None,
                model=None,
                user_id=None,
                event_type=None,
                payload={},
                delivery_latency_ms=None,
            )

def test_redis_adapter_rate_limiting() -> None:
    adapter = RedisAdapter("redis://localhost:6379/0")
    adapter.client = MagicMock()

    adapter.client.set.return_value = True
    assert adapter.acquire_rate_limit("rate:test", 60) is True
    adapter.client.set.assert_called_once()
    args, kwargs = adapter.client.set.call_args
    assert args[0] == "rate:test"
    assert kwargs["nx"] is True
    assert kwargs["ex"] == 60

    adapter.client.set.return_value = None
    assert adapter.acquire_rate_limit("rate:test", 60) is False

def test_redis_adapter_incident_lifecycle() -> None:
    adapter = RedisAdapter("redis://localhost:6379/0")
    adapter.client = MagicMock()

    adapter.client.get.return_value = b"inc-999"
    assert adapter.get_open_incident("gpt-4", "/chat") == "inc-999"
    adapter.client.get.assert_called_with("incident:pd:gpt-4:/chat")

    adapter.client.get.return_value = None
    assert adapter.get_open_incident("gpt-4", "/chat") is None

    adapter.set_open_incident("gpt-4", "/chat", "inc-100", 300)
    adapter.client.setex.assert_called_once_with("incident:pd:gpt-4:/chat", 300, "inc-100")

    adapter.delete_open_incident("gpt-4", "/chat")
    adapter.client.delete.assert_called_once_with("incident:pd:gpt-4:/chat")

def test_slack_adapter_send_channel_and_dm() -> None:
    adapter = SlackAdapter("http://localhost:8080/mock-slack")

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value.read.return_value = b"ok"

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        adapter.send_channel_message("#alerts-prod", "High cost anomaly detected")
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Content-type") == "application/json"
        data = json.loads(req.data.decode("utf-8"))
        assert data["channel"] == "#alerts-prod"
        assert data["text"] == "High cost anomaly detected"

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        adapter.send_direct_message("@owner-alice", "Budget 100% threshold reached")
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["channel"] == "@owner-alice"

def test_slack_adapter_handles_url_error() -> None:
    adapter = SlackAdapter("http://localhost:8080/mock-slack")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        adapter.send_channel_message("#alerts", "Should not raise uncaught exception")

def test_pagerduty_adapter_trigger_and_resolve() -> None:
    adapter = PagerDutyAdapter("pd-routing-key-123")

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value.read.return_value = b'{"status":"success","dedup_key":"custom-dedup"}'

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        dedup = adapter.trigger_incident(
            summary="P95 latency SLO breach",
            severity="critical",
            source="latency-monitor",
            custom_details={"model": "gpt-4", "endpoint": "/completions"},
        )
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["routing_key"] == "pd-routing-key-123"
        assert data["event_action"] == "trigger"
        assert data["payload"]["severity"] == "critical"
        assert data["dedup_key"] == "latency_slo:gpt-4:_completions"

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        adapter.resolve_incident("custom-dedup")
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["event_action"] == "resolve"
        assert data["dedup_key"] == "custom-dedup"

def test_prometheus_adapter_record_delivery_latency() -> None:
    adapter = PrometheusAdapter()
    adapter._histogram = MagicMock()
    mock_label = MagicMock()
    adapter._histogram.labels.return_value = mock_label

    adapter.record_delivery_latency("budget", "high", 45.2)
    adapter._histogram.labels.assert_called_once_with(type="budget", severity="high")
    mock_label.observe.assert_called_once_with(45.2)

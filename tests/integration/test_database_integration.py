from unittest.mock import MagicMock, patch
import pytest
from psycopg.errors import CheckViolation, UniqueViolation, IntegrityError

from adapters.postgres.postgres_adapter import PostgresAdapter
from shared.repositories.base_alert_repository import BaseAlertRepository
from shared.errors.application_error import ValidationError, ConflictError

class FakeIntegrityError(IntegrityError):
    def __init__(self, msg: str, constraint_name: str) -> None:
        super().__init__(msg)
        diag = MagicMock()
        diag.constraint_name = constraint_name
        self.diag = diag

def test_database_insert_alert_all_supported_types() -> None:
    alert_types = [
        ("budget", "billing", "gpt-4", "usr-1", "blocked", {"threshold": 1.0}),
        ("cost_anomaly", "inference", "claude-3", None, "anomaly", {"ewma": 3.4}),
        ("toxicity", "chat", "llama-3", "usr-2", "flagged", {"score": 0.94}),
        ("quality_degradation", "rag", "gpt-4o", None, "degradation", {"drop": 0.25}),
        ("latency_slo", "api", "mistral-large", None, "breach", {"p95": 1400}),
        ("latency_ttft_regression", "stream", "gemini-1.5", None, "regression", {"ttft_ms": 950}),
    ]

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        adapter = PostgresAdapter("postgresql://localhost:5432/test_db")
        for atype, svc, model, uid, evtype, payload in alert_types:
            adapter.insert_alert(
                alert_type=atype,
                service=svc,
                model=model,
                user_id=uid,
                event_type=evtype,
                payload=payload,
                delivery_latency_ms=80,
            )

    assert mock_cursor.execute.call_count == len(alert_types)
    assert mock_conn.commit.call_count == len(alert_types)

def test_database_constraint_mapping_integrations() -> None:
    test_cases = [
        ("alert_history_alert_type_ck", ValidationError),
        ("alert_history_payload_ck", ValidationError),
        ("alert_history_delivery_latency_ms_ck", ValidationError),
        ("alert_history_public_id_ck", ValidationError),
        ("alert_history_pkey", ConflictError),
    ]

    for constraint_name, expected_error in test_cases:
        exc = FakeIntegrityError(f"violates constraint {constraint_name}", constraint_name)
        mock_conn = MagicMock()
        mock_conn.__enter__.side_effect = exc

        with patch("psycopg.connect", return_value=mock_conn):
            adapter = PostgresAdapter("postgresql://localhost:5432/test_db")
            with pytest.raises(expected_error):
                adapter.insert_alert(
                    alert_type="bad_type",
                    service="svc",
                    model="model",
                    user_id="user",
                    event_type="ev",
                    payload={},
                    delivery_latency_ms=10,
                )

def test_base_alert_repository_wrapper_integration() -> None:
    mock_db_port = MagicMock()
    repo = BaseAlertRepository(mock_db_port)

    repo.insert_alert_history(
        alert_type="budget",
        service="billing",
        model="gpt-4",
        user_id="usr-99",
        event_type="blocked",
        payload={"spend": 500, "limit": 500},
        delivery_latency_ms=45,
    )

    mock_db_port.insert_alert.assert_called_once_with(
        alert_type="budget",
        service="billing",
        model="gpt-4",
        user_id="usr-99",
        event_type="blocked",
        payload={"spend": 500, "limit": 500},
        delivery_latency_ms=45,
    )

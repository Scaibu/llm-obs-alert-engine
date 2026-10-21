from http.server import HTTPServer
import threading
import socket
from unittest.mock import MagicMock, patch
import httpx
from opentelemetry import trace

from main import (
    _extract_traceparent,
    _init_tracing,
    _start_health_server,
    HealthCheckHandler,
)
from worker.registry import build_registry

def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])

def test_extract_traceparent_scenarios() -> None:
    valid_tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    headers_str = [("traceparent", valid_tp.encode("utf-8"))]
    ctx1 = _extract_traceparent(headers_str)
    assert ctx1 is not None

    headers_bytes = [(b"traceparent", valid_tp.encode("utf-8"))]
    ctx2 = _extract_traceparent(headers_bytes)
    assert ctx2 is not None

    headers_str_val = [("traceparent", valid_tp)]
    ctx3 = _extract_traceparent(headers_str_val)
    assert ctx3 is not None

    assert _extract_traceparent(None) is None
    assert _extract_traceparent([]) is None
    assert _extract_traceparent([("other-header", b"value")]) is None

def test_build_registry_maps_all_kafka_topics() -> None:
    registry = build_registry(
        budget_handler=MagicMock(),
        cost_anomaly_handler=MagicMock(),
        toxicity_handler=MagicMock(),
        degradation_handler=MagicMock(),
        latency_slo_handler=MagicMock(),
        latency_ttft_regression_handler=MagicMock(),
    )

    expected_topics = {
        "alerts.budget",
        "alerts.cost.anomaly",
        "llm.toxicity.flagged",
        "alerts.quality.degradation",
        "alerts.latency.slo",
        "alerts.latency.ttft_regression",
    }
    assert set(registry.keys()) == expected_topics

def test_init_tracing_runs_cleanly() -> None:
    with patch("main.TracerProvider") as mock_provider, \
         patch("main.trace.set_tracer_provider"):
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        _init_tracing()
        mock_provider_instance.add_span_processor.assert_called_once()

def test_health_check_server_endpoints() -> None:
    port = _get_free_port()
    server = HTTPServer(("127.0.0.1", port), HealthCheckHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
            resp_health = client.get("/healthz")
            assert resp_health.status_code == 200
            data_health = resp_health.json()
            assert data_health["status"] == "ok"
            assert data_health["service"] == "alert-engine"

            resp_ready = client.get("/readyz")
            assert resp_ready.status_code == 200
            data_ready = resp_ready.json()
            assert data_ready["status"] == "ready"

            resp_not_found = client.get("/unknown-route")
            assert resp_not_found.status_code == 404
    finally:
        server.shutdown()
        server.server_close()

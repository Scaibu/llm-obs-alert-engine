import json
import logging
import signal
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from confluent_kafka import Consumer, KafkaError
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from prometheus_client import start_http_server

from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.context import Context

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(repo_root / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "src"))

from config.config import load_config
from worker.registry import build_registry
from adapters.postgres.postgres_adapter import PostgresAdapter
from adapters.redis.redis_adapter import RedisAdapter
from adapters.notification_senders.slack_adapter import SlackAdapter
from adapters.notification_senders.pagerduty_adapter import PagerDutyAdapter
from adapters.metrics.prometheus_adapter import PrometheusAdapter
from handlers.alerts_budget.handler import BudgetAlertHandler
from handlers.alerts_cost_anomaly.handler import CostAnomalyAlertHandler
from handlers.alerts_toxicity.handler import ToxicityAlertHandler
from handlers.alerts_quality_degradation.handler import QualityDegradationAlertHandler
from handlers.alerts_latency_slo.handler import LatencySloAlertHandler
from handlers.alerts_latency_ttft_regression.handler import LatencyTtftRegressionAlertHandler

logger = logging.getLogger(__name__)

SERVICE_NAME = "alert-engine"
tracer = trace.get_tracer(SERVICE_NAME)

def _init_tracing() -> None:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

def _extract_traceparent(headers: Any) -> Context | None:
    if not headers:
        return None
    carrier: dict[str, str] = {}
    for item in headers:
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            continue
        key, value = item[0], item[1]
        if value is None:
            continue
        key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
        decoded = value.decode("utf-8") if isinstance(value, bytes) else str(value)
        if key_str == "traceparent":
            carrier["traceparent"] = decoded
        elif key_str == "tracestate":
            carrier["tracestate"] = decoded
    if not carrier:
        return None
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(carrier)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"alert-engine"}')
        elif self.path == "/readyz":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ready"}')
        elif self.path in ("/", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')

    def log_message(self, format: str, *args: Any) -> None:
        pass

_HealthHandler = HealthCheckHandler

def _start_health_server(port: int) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def main() -> None:
    shutdown_event = threading.Event()

    def _signal_handler(signum: int, frame: Any) -> None:
        shutdown_event.set()

    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
    except (ValueError, AttributeError):
        pass

    _init_tracing()
    config = load_config()
    _start_health_server(config.health_check_port)
    
    try:
        start_http_server(config.prometheus_metrics_port)
    except OSError:
        pass

    postgres_adapter = PostgresAdapter(config.postgres_dsn)
    redis_adapter = RedisAdapter(config.redis_url)
    slack_adapter = SlackAdapter(
        webhook_url=config.slack_webhook_url,
        timeout_seconds=config.slack_timeout_seconds,
    )
    pagerduty_adapter = PagerDutyAdapter(
        routing_key=config.pagerduty_routing_key,
        endpoint=config.pagerduty_endpoint,
        timeout_seconds=config.pagerduty_timeout_seconds,
    )
    metrics_adapter = PrometheusAdapter()

    budget_handler = BudgetAlertHandler(
        db_port=postgres_adapter,
        redis_port=redis_adapter,
        slack_port=slack_adapter,
        metrics_port=metrics_adapter,
        service_owners_path=config.service_owners_file_path,
    )

    cost_anomaly_handler = CostAnomalyAlertHandler(
        db_port=postgres_adapter,
        redis_port=redis_adapter,
        slack_port=slack_adapter,
        pagerduty_port=pagerduty_adapter,
        metrics_port=metrics_adapter,
    )

    toxicity_handler = ToxicityAlertHandler(
        redis_port=redis_adapter,
        slack_port=slack_adapter,
    )

    degradation_handler = QualityDegradationAlertHandler(
        redis_port=redis_adapter,
        slack_port=slack_adapter,
    )

    latency_slo_handler = LatencySloAlertHandler(
        db_port=postgres_adapter,
        redis_port=redis_adapter,
        slack_port=slack_adapter,
        pagerduty_port=pagerduty_adapter,
        metrics_port=metrics_adapter,
    )

    latency_ttft_regression_handler = LatencyTtftRegressionAlertHandler(
        db_port=postgres_adapter,
        redis_port=redis_adapter,
        slack_port=slack_adapter,
        metrics_port=metrics_adapter,
    )

    handlers_registry = build_registry(
        budget_handler=budget_handler.handle,
        cost_anomaly_handler=cost_anomaly_handler.handle,
        toxicity_handler=toxicity_handler.handle,
        degradation_handler=degradation_handler.handle,
        latency_slo_handler=latency_slo_handler.handle,
        latency_ttft_regression_handler=latency_ttft_regression_handler.handle,
    )

    consumer = Consumer({
        "bootstrap.servers": config.kafka_bootstrap_servers,
        "group.id": config.kafka_consumer_group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe(config.kafka_topics)

    logger.info("alert-engine worker started, consuming %s", config.kafka_topics)

    try:
        while not shutdown_event.is_set():
            msg = consumer.poll(1.0)
            if msg is None:
                continue

            err = msg.error()
            if err is not None:
                if err.code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Kafka error: %s", err)
                continue

            topic = msg.topic()
            if topic is None:
                continue
            handler_def = handlers_registry.get(topic)
            if not handler_def:
                consumer.commit(message=msg, asynchronous=False)
                continue

            msg_val = msg.value()
            if msg_val is None:
                consumer.commit(message=msg, asynchronous=False)
                continue

            parent_ctx = _extract_traceparent(msg.headers())

            with tracer.start_as_current_span(
                "alert_engine.process_message",
                context=parent_ctx,
                attributes={
                    "service.name": SERVICE_NAME,
                    "messaging.system": "kafka",
                    "messaging.destination": topic,
                },
            ):
                try:
                    payload = json.loads(msg_val.decode("utf-8"))
                    handler_def.handler(payload)
                except Exception:
                    logger.exception("Failed to process message on topic %s", topic)

            consumer.commit(message=msg, asynchronous=False)

    finally:
        consumer.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

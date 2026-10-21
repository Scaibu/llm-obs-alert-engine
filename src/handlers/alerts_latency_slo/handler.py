import logging
from typing import Any
from opentelemetry import trace
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.pagerduty_port import PagerDutyPort
from ports.metrics_port import MetricsPort
from features.latency_slo.index import (
    LatencySloService,
    LatencySloAlertPayload,
    LatencySloSchemaMapper,
)

logger = logging.getLogger(__name__)

class LatencySloAlertHandler:
    def __init__(
        self,
        db_port: DbPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        pagerduty_port: PagerDutyPort,
        metrics_port: MetricsPort
    ) -> None:
        self.service = LatencySloService(
            db_port=db_port,
            redis_port=redis_port,
            slack_port=slack_port,
            pagerduty_port=pagerduty_port,
            metrics_port=metrics_port
        )

    def handle(self, payload: dict[str, Any]) -> None:
        feature_payload = LatencySloSchemaMapper.from_api(payload)
        self.service.process_alert(feature_payload)


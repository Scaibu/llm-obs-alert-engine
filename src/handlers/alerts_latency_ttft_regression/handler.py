import logging
from typing import Any
from ports.db_port import DbPort
from ports.redis_port import RedisPort
from ports.slack_port import SlackPort
from ports.metrics_port import MetricsPort
from features.latency_ttft_regression.index import (
    LatencyTtftRegressionService,
    LatencyTtftRegressionAlertPayload,
    LatencyTtftRegressionSchemaMapper,
)

logger = logging.getLogger(__name__)

class LatencyTtftRegressionAlertHandler:
    def __init__(
        self,
        db_port: DbPort,
        redis_port: RedisPort,
        slack_port: SlackPort,
        metrics_port: MetricsPort
    ) -> None:
        self.service = LatencyTtftRegressionService(
            db_port=db_port,
            redis_port=redis_port,
            slack_port=slack_port,
            metrics_port=metrics_port
        )

    def handle(self, payload: dict[str, Any]) -> None:
        feature_payload = LatencyTtftRegressionSchemaMapper.from_api(payload)
        self.service.process_alert(feature_payload)


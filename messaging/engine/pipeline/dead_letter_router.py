from typing import Any
from confluent_kafka import Producer
import json

class DeadLetterRouter:
    def __init__(self, producer: Producer, dlq_topic: str = "alerts.dlq") -> None:
        self._producer = producer
        self._dlq_topic = dlq_topic

    def route_to_dlq(self, original_topic: str, original_payload: Any, error_reason: str) -> None:
        dlq_message = {
            "original_topic": original_topic,
            "error_reason": error_reason,
            "payload": original_payload,
        }
        self._producer.produce(
            topic=self._dlq_topic,
            value=json.dumps(dlq_message).encode("utf-8"),
        )
        self._producer.poll(0)

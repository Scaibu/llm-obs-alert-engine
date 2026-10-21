import json
from typing import Any
from confluent_kafka import Producer

class EventPublisher:
    def __init__(self, producer: Producer) -> None:
        self._producer = producer

    def publish(self, topic: str, key: str, value: dict[str, Any]) -> None:
        encoded_key = key.encode("utf-8")
        encoded_value = json.dumps(value).encode("utf-8")
        self._producer.produce(topic=topic, key=encoded_key, value=encoded_value)
        self._producer.poll(0)

    def flush(self, timeout_seconds: float = 5.0) -> int:
        return self._producer.flush(timeout=timeout_seconds)

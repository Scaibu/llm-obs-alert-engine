from confluent_kafka import Consumer

class ManagedConsumerGroup:
    def __init__(self, consumer: Consumer, topics: list[str]) -> None:
        self._consumer = consumer
        self._topics = topics

    def start(self) -> None:
        self._consumer.subscribe(self._topics)

    def close(self) -> None:
        self._consumer.close()

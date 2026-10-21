from confluent_kafka import Consumer, Producer

class KafkaConnectionPool:
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers

    def create_consumer(self, group_id: str, auto_offset_reset: str = "earliest") -> Consumer:
        return Consumer({
            "bootstrap.servers": self._bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": False,
        })

    def create_producer(self) -> Producer:
        return Producer({
            "bootstrap.servers": self._bootstrap_servers,
        })

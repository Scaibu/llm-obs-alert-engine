from confluent_kafka.admin import AdminClient

class ClusterHealthChecker:
    def __init__(self, bootstrap_servers: str) -> None:
        self._admin = AdminClient({"bootstrap.servers": bootstrap_servers})

    def is_healthy(self, timeout_seconds: float = 5.0) -> bool:
        try:
            metadata = self._admin.list_topics(timeout=timeout_seconds)
            return len(metadata.brokers) > 0
        except Exception:
            return False

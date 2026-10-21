from typing import Any
from ports.db_port import DbPort

class BaseAlertRepository:
    def __init__(self, db_port: DbPort) -> None:
        self._db_port = db_port

    def insert_alert_history(
        self,
        alert_type: str,
        service: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        event_type: str | None = None,
        payload: dict[str, Any] | None = None,
        delivery_latency_ms: int | None = None,
    ) -> None:
        self._db_port.insert_alert(
            alert_type=alert_type,
            service=service,
            model=model,
            user_id=user_id,
            event_type=event_type,
            payload=payload or {},
            delivery_latency_ms=delivery_latency_ms,
        )

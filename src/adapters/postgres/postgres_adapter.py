import json
import psycopg
from typing import Any
from opentelemetry import trace
from ports.db_port import DbPort
from shared.errors.db_error_mapping import map_db_constraint_error

tracer = trace.get_tracer("alert-engine")

class PostgresAdapter(DbPort):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def insert_alert(
        self,
        alert_type: str,
        service: str | None,
        model: str | None,
        user_id: str | None,
        event_type: str | None,
        payload: dict[str, Any],
        delivery_latency_ms: int | None
    ) -> None:
        query = """
        INSERT INTO alert_history (
            alert_type, service, model, user_id, event_type, payload, delivery_latency_ms
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        with tracer.start_as_current_span(
            "postgres_adapter.insert_alert",
            attributes={
                "db.system": "postgresql",
                "db.operation": "insert",
                "db.sql": query.strip(),
                "alert.type": alert_type,
                "event.type": event_type or "",
            }
        ) as span:
            try:
                with psycopg.connect(self.dsn) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            query,
                            (
                                alert_type,
                                service,
                                model,
                                user_id,
                                event_type,
                                json.dumps(payload),
                                delivery_latency_ms
                            )
                        )
                    conn.commit()
            except psycopg.errors.IntegrityError as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                constraint_name = getattr(getattr(e, "diag", None), "constraint_name", None) or ""
                mapped_error = map_db_constraint_error(constraint_name, str(e))
                raise mapped_error from e
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise

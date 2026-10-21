from typing import Any
import psycopg

class QueryExecutor:
    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self._conn = conn

    def execute(self, sql: str, params: tuple[Any, ...] | dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchall()
            return []

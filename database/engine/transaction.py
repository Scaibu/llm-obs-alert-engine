from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
import psycopg

class TransactionManager:
    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self._conn = conn

    @contextmanager
    def transaction(self) -> Generator[psycopg.Connection[Any], None, None]:
        with self._conn.transaction():
            yield self._conn

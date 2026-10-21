from typing import Any
import psycopg

class DatabaseConnection:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn)

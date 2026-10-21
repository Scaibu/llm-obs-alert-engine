from pathlib import Path
from typing import Any
import psycopg

class MigrationRunner:
    def __init__(self, dsn: str, migrations_dir: Path) -> None:
        self._dsn = dsn
        self._migrations_dir = migrations_dir

    def apply(self, sql_filename: str) -> None:
        target = self._migrations_dir / sql_filename
        sql = target.read_text(encoding="utf-8")
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

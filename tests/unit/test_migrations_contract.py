from pathlib import Path
import re
from shared.errors.db_error_mapping import CONSTRAINT_ERROR_MAP

REQUIRED_HEADER_KEYS = [
    "migration",
    "description",
    "author",
    "date",
    "depends_on",
    "reversible",
    "lock_risk",
    "rows_affected",
    "reason",
]

def test_migration_files_and_headers() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    migrations_dir = root_dir / "database" / "migrations" / "sql"
    assert migrations_dir.exists(), "Migrations SQL directory must exist"

    sql_files = sorted([f for f in migrations_dir.glob("*.sql") if not f.name.endswith(".rollback.sql")])
    assert len(sql_files) > 0, "At least one forward migration must exist"

    for sql_file in sql_files:
        version_prefix = sql_file.name.split("_")[0]
        assert re.match(r"^\d{4}$", version_prefix), f"Migration prefix must be 4 digits: {sql_file.name}"

        rollback_file = sql_file.with_name(f"{sql_file.stem}.rollback.sql")
        assert rollback_file.exists(), f"Rollback file must exist for {sql_file.name}"

        for target in (sql_file, rollback_file):
            content = target.read_text(encoding="utf-8")
            for key in REQUIRED_HEADER_KEYS:
                pattern = rf"^--\s*{key}:"
                assert re.search(pattern, content, re.MULTILINE), f"Missing header '{key}' in {target.name}"

def test_schema_lock_consistency() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    lock_file = root_dir / "database" / "schema.lock"
    assert lock_file.exists(), "schema.lock must exist"

    lock_version = lock_file.read_text(encoding="utf-8").strip()
    assert re.match(r"^\d{4}$", lock_version), f"schema.lock must contain a 4-digit version, got: {lock_version}"

    migrations_dir = root_dir / "database" / "migrations" / "sql"
    sql_files = sorted([f for f in migrations_dir.glob("*.sql") if not f.name.endswith(".rollback.sql")])
    latest_prefix = sql_files[-1].name.split("_")[0]
    assert lock_version == latest_prefix, f"schema.lock version {lock_version} does not match latest migration {latest_prefix}"

def test_database_constraint_error_map_coverage() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    init_sql = root_dir / "database" / "migrations" / "sql" / "0001_init.sql"
    content = init_sql.read_text(encoding="utf-8")

    constraint_matches = re.findall(r"CONSTRAINT\s+([a-zA-Z0-9_]+)\s+", content)
    assert len(constraint_matches) > 0

    for constraint in constraint_matches:
        if constraint.endswith("_pkey"):
            continue
        assert constraint in CONSTRAINT_ERROR_MAP, f"Constraint '{constraint}' has no error mapping in CONSTRAINT_ERROR_MAP"

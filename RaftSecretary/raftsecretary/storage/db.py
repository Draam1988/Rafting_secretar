from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

CURRENT_SCHEMA_VERSION = 1
CURRENT_APP_VERSION = "v.0.2.7"


def create_competition_db(db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(_schema_sql())
        connection.executemany(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
            [
                ("schema_version", str(CURRENT_SCHEMA_VERSION)),
                ("app_version", CURRENT_APP_VERSION),
            ],
        )
        connection.commit()
    return db_path


def list_competition_dbs(data_dir: Path) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    return sorted(path for path in data_dir.iterdir() if path.suffix == ".db")


def delete_competition_db(data_dir: Path, db_name: str) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / db_name
    if db_path.suffix != ".db":
        return
    if not db_path.exists():
        return
    db_path.unlink()


def read_app_meta(db_path: Path) -> dict[str, str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT key, value FROM app_meta"
        ).fetchall()
    return {str(key): str(value) for key, value in rows}


def is_supported_import_db(db_path: Path) -> bool:
    try:
        meta = read_app_meta(db_path)
    except sqlite3.Error:
        return False
    schema_version = meta.get("schema_version", "").strip()
    if not schema_version:
        return True
    try:
        return int(schema_version) <= CURRENT_SCHEMA_VERSION
    except ValueError:
        return False


def inspect_uploaded_db_bytes(file_data: bytes) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(file_data)
        tmp_path = Path(tmp.name)
    try:
        if not is_supported_import_db(tmp_path):
            try:
                meta = read_app_meta(tmp_path)
            except sqlite3.Error:
                return (False, "invalid")
            schema_version = meta.get("schema_version", "").strip()
            if schema_version:
                try:
                    if int(schema_version) > CURRENT_SCHEMA_VERSION:
                        return (False, "incompatible")
                except ValueError:
                    return (False, "invalid")
            return (False, "invalid")
        return (True, "")
    finally:
        tmp_path.unlink(missing_ok=True)


def _schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")

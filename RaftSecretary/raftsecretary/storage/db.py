from __future__ import annotations

import sqlite3
from pathlib import Path


def create_competition_db(db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(_schema_sql())
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


def _schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")

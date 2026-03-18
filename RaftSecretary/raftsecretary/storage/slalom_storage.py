from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SlalomRunRecord:
    team_name: str
    attempt_number: int
    base_time_seconds: int
    finish_time_seconds: int
    gate_penalties: list[int]


def save_slalom_run(
    db_path: Path,
    category_key: str,
    team_name: str,
    attempt_number: int,
    base_time_seconds: int,
    gate_penalties: list[int],
    finish_time_seconds: int = 0,
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_slalom_schema(connection)
        connection.execute(
            """
            DELETE FROM slalom_runs
            WHERE category_key = ? AND team_name = ? AND attempt_number = ?
            """,
            (category_key, team_name, attempt_number),
        )
        connection.execute(
            """
            INSERT INTO slalom_runs (
                category_key, team_name, attempt_number, base_time_seconds, finish_time_seconds, gate_penalties
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                category_key,
                team_name,
                attempt_number,
                base_time_seconds,
                finish_time_seconds,
                ",".join(str(value) for value in gate_penalties),
            ),
        )
        connection.commit()


def load_slalom_runs(db_path: Path, category_key: str) -> list[SlalomRunRecord]:
    with sqlite3.connect(db_path) as connection:
        _ensure_slalom_schema(connection)
        rows = connection.execute(
            """
            SELECT team_name, attempt_number, base_time_seconds, finish_time_seconds, gate_penalties
            FROM slalom_runs
            WHERE category_key = ?
            ORDER BY team_name, attempt_number
            """,
            (category_key,),
        ).fetchall()

    return [
        SlalomRunRecord(
            team_name=row[0],
            attempt_number=row[1],
            base_time_seconds=row[2],
            finish_time_seconds=row[3],
            gate_penalties=[int(value) for value in row[4].split(",") if value],
        )
        for row in rows
    ]


def save_slalom_lineup_flags(
    db_path: Path,
    category_key: str,
    lineup_flags: dict[str, dict[int, bool]],
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_slalom_schema(connection)
        connection.execute(
            "DELETE FROM slalom_lineup_flags WHERE category_key = ?",
            (category_key,),
        )
        rows = []
        for team_name, member_flags in lineup_flags.items():
            for member_order, is_active in member_flags.items():
                rows.append((category_key, team_name, member_order, 1 if is_active else 0))
        connection.executemany(
            """
            INSERT INTO slalom_lineup_flags (
                category_key,
                team_name,
                member_order,
                is_active
            ) VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def load_slalom_lineup_flags(
    db_path: Path,
    category_key: str,
) -> dict[str, dict[int, bool]]:
    with sqlite3.connect(db_path) as connection:
        _ensure_slalom_schema(connection)
        rows = connection.execute(
            """
            SELECT team_name, member_order, is_active
            FROM slalom_lineup_flags
            WHERE category_key = ?
            ORDER BY team_name, member_order
            """,
            (category_key,),
        ).fetchall()
    result: dict[str, dict[int, bool]] = {}
    for team_name, member_order, is_active in rows:
        result.setdefault(team_name, {})[member_order] = bool(is_active)
    return result


def clear_slalom_category(db_path: Path, category_key: str) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_slalom_schema(connection)
        connection.execute(
            "DELETE FROM slalom_runs WHERE category_key = ?",
            (category_key,),
        )
        connection.execute(
            "DELETE FROM slalom_lineup_flags WHERE category_key = ?",
            (category_key,),
        )
        connection.commit()


def _ensure_slalom_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS slalom_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            team_name TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            base_time_seconds INTEGER NOT NULL,
            gate_penalties TEXT NOT NULL
        )
        """
    )
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(slalom_runs)").fetchall()
    }
    if "finish_time_seconds" not in columns:
        connection.execute(
            "ALTER TABLE slalom_runs ADD COLUMN finish_time_seconds INTEGER NOT NULL DEFAULT 0"
        )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS slalom_lineup_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            team_name TEXT NOT NULL,
            member_order INTEGER NOT NULL,
            is_active INTEGER NOT NULL,
            UNIQUE(category_key, team_name, member_order)
        )
        """
    )

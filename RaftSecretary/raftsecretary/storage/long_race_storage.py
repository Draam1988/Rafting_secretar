from __future__ import annotations

import sqlite3
from pathlib import Path

from raftsecretary.domain.sprint import SprintEntry


def save_long_race_entries(
    db_path: Path,
    category_key: str,
    entries: list[SprintEntry],
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_long_race_schema(connection)
        connection.execute(
            "DELETE FROM long_race_results WHERE category_key = ?",
            (category_key,),
        )
        connection.executemany(
            """
            INSERT INTO long_race_results (
                category_key,
                team_name,
                start_order,
                start_time,
                base_time_seconds,
                buoy_penalty_seconds,
                behavior_penalty_seconds,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    category_key,
                    entry.team_name,
                    entry.start_order,
                    entry.start_time,
                    entry.base_time_seconds,
                    entry.buoy_penalty_seconds,
                    entry.behavior_penalty_seconds,
                    entry.status,
                )
                for entry in entries
            ],
        )
        connection.commit()


def load_long_race_entries(db_path: Path, category_key: str) -> list[SprintEntry]:
    with sqlite3.connect(db_path) as connection:
        _ensure_long_race_schema(connection)
        rows = connection.execute(
            """
            SELECT
                team_name,
                start_order,
                start_time,
                base_time_seconds,
                buoy_penalty_seconds,
                behavior_penalty_seconds,
                status
            FROM long_race_results
            WHERE category_key = ?
            ORDER BY start_order, id
            """,
            (category_key,),
        ).fetchall()

    return [
        SprintEntry(
            team_name=row[0],
            start_order=row[1],
            start_time=row[2],
            base_time_seconds=row[3],
            buoy_penalty_seconds=row[4],
            behavior_penalty_seconds=row[5],
            status=row[6],
        )
        for row in rows
    ]


def save_long_race_lineup_flags(
    db_path: Path,
    category_key: str,
    lineup_flags: dict[str, dict[int, bool]],
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_long_race_schema(connection)
        connection.execute(
            "DELETE FROM long_race_lineup_flags WHERE category_key = ?",
            (category_key,),
        )
        rows = []
        for team_name, member_flags in lineup_flags.items():
            for member_order, is_active in member_flags.items():
                rows.append((category_key, team_name, member_order, 1 if is_active else 0))
        connection.executemany(
            """
            INSERT INTO long_race_lineup_flags (
                category_key,
                team_name,
                member_order,
                is_active
            ) VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def load_long_race_lineup_flags(
    db_path: Path,
    category_key: str,
) -> dict[str, dict[int, bool]]:
    with sqlite3.connect(db_path) as connection:
        _ensure_long_race_schema(connection)
        rows = connection.execute(
            """
            SELECT team_name, member_order, is_active
            FROM long_race_lineup_flags
            WHERE category_key = ?
            ORDER BY team_name, member_order
            """,
            (category_key,),
        ).fetchall()
    result: dict[str, dict[int, bool]] = {}
    for team_name, member_order, is_active in rows:
        result.setdefault(team_name, {})[member_order] = bool(is_active)
    return result


def _ensure_long_race_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS long_race_lineup_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            team_name TEXT NOT NULL,
            member_order INTEGER NOT NULL,
            is_active INTEGER NOT NULL,
            UNIQUE(category_key, team_name, member_order)
        )
        """
    )
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(long_race_results)").fetchall()
    }
    if "start_time" not in columns:
        connection.execute(
            "ALTER TABLE long_race_results ADD COLUMN start_time TEXT NOT NULL DEFAULT ''"
        )

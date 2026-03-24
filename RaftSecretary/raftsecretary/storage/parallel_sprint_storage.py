from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from raftsecretary.domain.parallel_sprint import ParallelSprintHeatResult
from raftsecretary.domain.sprint import SprintEntry


@dataclass(frozen=True)
class ParallelSprintHeatMeta:
    round_name: str
    scheduled_start_time: str
    left_base_time_seconds: int
    left_penalty_seconds: int
    right_base_time_seconds: int
    right_penalty_seconds: int
    winner_team_name: str


def save_parallel_sprint_heat(
    db_path: Path,
    category_key: str,
    round_name: str,
    left: ParallelSprintHeatResult,
    right: ParallelSprintHeatResult,
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            """
            DELETE FROM parallel_sprint_heats
            WHERE category_key = ? AND round_name = ?
            """,
            (category_key, round_name),
        )
        connection.execute(
            """
            INSERT INTO parallel_sprint_heats (
                category_key,
                round_name,
                left_team_name,
                left_start_order,
                left_total_time_seconds,
                left_missed_buoys,
                left_status,
                right_team_name,
                right_start_order,
                right_total_time_seconds,
                right_missed_buoys,
                right_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category_key,
                round_name,
                left.team_name,
                left.start_order,
                left.total_time_seconds,
                left.missed_buoys,
                left.status,
                right.team_name,
                right.start_order,
                right.total_time_seconds,
                right.missed_buoys,
                right.status,
            ),
        )
        connection.commit()


def load_parallel_sprint_heats(
    db_path: Path,
    category_key: str,
) -> list[tuple[str, ParallelSprintHeatResult, ParallelSprintHeatResult]]:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        rows = connection.execute(
            """
            SELECT
                round_name,
                left_team_name,
                left_start_order,
                left_total_time_seconds,
                left_missed_buoys,
                left_status,
                right_team_name,
                right_start_order,
                right_total_time_seconds,
                right_missed_buoys,
                right_status
            FROM parallel_sprint_heats
            WHERE category_key = ?
            ORDER BY round_name, id
            """,
            (category_key,),
        ).fetchall()

    return [
        (
            row[0],
            ParallelSprintHeatResult(
                team_name=row[1],
                lane="left",
                start_order=row[2],
                total_time_seconds=row[3],
                missed_buoys=row[4],
                status=row[5],
            ),
            ParallelSprintHeatResult(
                team_name=row[6],
                lane="right",
                start_order=row[7],
                total_time_seconds=row[8],
                missed_buoys=row[9],
                status=row[10],
            ),
        )
        for row in rows
    ]


def save_parallel_sprint_heat_meta(
    db_path: Path,
    category_key: str,
    meta: ParallelSprintHeatMeta,
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            """
            INSERT INTO parallel_sprint_heat_meta (
                category_key,
                round_name,
                scheduled_start_time,
                left_base_time_seconds,
                left_penalty_seconds,
                right_base_time_seconds,
                right_penalty_seconds,
                winner_team_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category_key, round_name) DO UPDATE SET
                scheduled_start_time = excluded.scheduled_start_time,
                left_base_time_seconds = excluded.left_base_time_seconds,
                left_penalty_seconds = excluded.left_penalty_seconds,
                right_base_time_seconds = excluded.right_base_time_seconds,
                right_penalty_seconds = excluded.right_penalty_seconds,
                winner_team_name = excluded.winner_team_name
            """,
            (
                category_key,
                meta.round_name,
                meta.scheduled_start_time,
                meta.left_base_time_seconds,
                meta.left_penalty_seconds,
                meta.right_base_time_seconds,
                meta.right_penalty_seconds,
                meta.winner_team_name,
            ),
        )
        connection.commit()


def load_parallel_sprint_heat_meta(
    db_path: Path,
    category_key: str,
) -> dict[str, ParallelSprintHeatMeta]:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        rows = connection.execute(
            """
            SELECT
                round_name,
                scheduled_start_time,
                left_base_time_seconds,
                left_penalty_seconds,
                right_base_time_seconds,
                right_penalty_seconds,
                winner_team_name
            FROM parallel_sprint_heat_meta
            WHERE category_key = ?
            ORDER BY round_name
            """,
            (category_key,),
        ).fetchall()
    return {
        row[0]: ParallelSprintHeatMeta(
            round_name=row[0],
            scheduled_start_time=row[1],
            left_base_time_seconds=row[2],
            left_penalty_seconds=row[3],
            right_base_time_seconds=row[4],
            right_penalty_seconds=row[5],
            winner_team_name=row[6],
        )
        for row in rows
    }


def _ensure_parallel_sprint_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS parallel_sprint_heat_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            round_name TEXT NOT NULL,
            scheduled_start_time TEXT NOT NULL DEFAULT '',
            left_base_time_seconds INTEGER NOT NULL DEFAULT 0,
            left_penalty_seconds INTEGER NOT NULL DEFAULT 0,
            right_base_time_seconds INTEGER NOT NULL DEFAULT 0,
            right_penalty_seconds INTEGER NOT NULL DEFAULT 0,
            winner_team_name TEXT NOT NULL DEFAULT '',
            UNIQUE(category_key, round_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS parallel_sprint_start_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            team_name TEXT NOT NULL,
            start_order INTEGER NOT NULL,
            start_time TEXT NOT NULL DEFAULT '',
            UNIQUE(category_key, team_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS parallel_sprint_lineup_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            team_name TEXT NOT NULL,
            member_order INTEGER NOT NULL,
            is_active INTEGER NOT NULL,
            UNIQUE(category_key, team_name, member_order)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS parallel_sprint_seeding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            seed_position INTEGER NOT NULL,
            team_name TEXT NOT NULL DEFAULT '',
            UNIQUE(category_key, seed_position)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS parallel_sprint_manual_mode (
            category_key TEXT PRIMARY KEY,
            manual INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def save_parallel_sprint_start_entries(
    db_path: Path,
    category_key: str,
    entries: list[SprintEntry],
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            "DELETE FROM parallel_sprint_start_entries WHERE category_key = ?",
            (category_key,),
        )
        connection.executemany(
            """
            INSERT INTO parallel_sprint_start_entries (
                category_key,
                team_name,
                start_order,
                start_time
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    category_key,
                    entry.team_name,
                    entry.start_order,
                    entry.start_time,
                )
                for entry in entries
            ],
        )
        connection.commit()


def load_parallel_sprint_start_entries(
    db_path: Path,
    category_key: str,
) -> list[SprintEntry]:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        rows = connection.execute(
            """
            SELECT team_name, start_order, start_time
            FROM parallel_sprint_start_entries
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
            base_time_seconds=0,
            buoy_penalty_seconds=0,
            behavior_penalty_seconds=0,
            status="OK",
        )
        for row in rows
    ]


def save_parallel_sprint_lineup_flags(
    db_path: Path,
    category_key: str,
    lineup_flags: dict[str, dict[int, bool]],
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            "DELETE FROM parallel_sprint_lineup_flags WHERE category_key = ?",
            (category_key,),
        )
        rows = []
        for team_name, member_flags in lineup_flags.items():
            for member_order, is_active in member_flags.items():
                rows.append((category_key, team_name, member_order, 1 if is_active else 0))
        connection.executemany(
            """
            INSERT INTO parallel_sprint_lineup_flags (
                category_key,
                team_name,
                member_order,
                is_active
            ) VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def load_parallel_sprint_lineup_flags(
    db_path: Path,
    category_key: str,
) -> dict[str, dict[int, bool]]:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        rows = connection.execute(
            """
            SELECT team_name, member_order, is_active
            FROM parallel_sprint_lineup_flags
            WHERE category_key = ?
            ORDER BY team_name, member_order
            """,
            (category_key,),
        ).fetchall()
    result: dict[str, dict[int, bool]] = {}
    for team_name, member_order, is_active in rows:
        result.setdefault(team_name, {})[member_order] = bool(is_active)
    return result


def clear_parallel_sprint_protocol(
    db_path: Path,
    category_key: str,
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute("DELETE FROM parallel_sprint_heats WHERE category_key = ?", (category_key,))
        connection.execute("DELETE FROM parallel_sprint_heat_meta WHERE category_key = ?", (category_key,))
        connection.execute("DELETE FROM parallel_sprint_start_entries WHERE category_key = ?", (category_key,))
        connection.execute("DELETE FROM parallel_sprint_lineup_flags WHERE category_key = ?", (category_key,))
        connection.commit()


def clear_parallel_sprint_rounds(
    db_path: Path,
    category_key: str,
    round_names: list[str],
) -> None:
    if not round_names:
        return
    placeholders = ", ".join("?" for _ in round_names)
    params = [category_key, *round_names]
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            f"DELETE FROM parallel_sprint_heats WHERE category_key = ? AND round_name IN ({placeholders})",
            params,
        )
        connection.execute(
            f"DELETE FROM parallel_sprint_heat_meta WHERE category_key = ? AND round_name IN ({placeholders})",
            params,
        )
        connection.commit()


def get_seeding(db_path: Path, category_key: str) -> list[str]:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        rows = connection.execute(
            "SELECT team_name FROM parallel_sprint_seeding WHERE category_key = ? ORDER BY seed_position",
            (category_key,),
        ).fetchall()
    return [row[0] for row in rows]


def save_seeding(db_path: Path, category_key: str, team_names: list[str]) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            "DELETE FROM parallel_sprint_seeding WHERE category_key = ?",
            (category_key,),
        )
        connection.executemany(
            "INSERT INTO parallel_sprint_seeding (category_key, seed_position, team_name) VALUES (?, ?, ?)",
            [(category_key, i + 1, name) for i, name in enumerate(team_names)],
        )
        connection.commit()


def clear_seeding(db_path: Path, category_key: str) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            "DELETE FROM parallel_sprint_seeding WHERE category_key = ?",
            (category_key,),
        )
        connection.commit()


def get_manual_mode(db_path: Path, category_key: str) -> bool:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        row = connection.execute(
            "SELECT manual FROM parallel_sprint_manual_mode WHERE category_key = ?",
            (category_key,),
        ).fetchone()
    return bool(row[0]) if row else False


def set_manual_mode(db_path: Path, category_key: str, manual: bool) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_parallel_sprint_schema(connection)
        connection.execute(
            """
            INSERT INTO parallel_sprint_manual_mode (category_key, manual) VALUES (?, ?)
            ON CONFLICT(category_key) DO UPDATE SET manual = excluded.manual
            """,
            (category_key, 1 if manual else 0),
        )
        connection.commit()

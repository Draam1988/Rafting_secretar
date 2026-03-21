from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from raftsecretary.domain.models import Category


@dataclass(frozen=True)
class CompetitionSettingsRecord:
    name: str
    competition_date: str
    description: str
    enabled_disciplines: list[str]
    categories: list[Category]
    slalom_gate_count: int
    competition_dates: list[str] = field(default_factory=list)
    organizer: str = field(default="", compare=False)  # display compat, derived from organizers on load
    organizers: list[str] = field(default_factory=list)
    venue: str = ""


def save_competition_settings(
    db_path: Path,
    settings: CompetitionSettingsRecord,
) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_competition_schema(connection)
        connection.execute(
            """
            INSERT INTO competition_settings (
                id, name, competition_date, description, organizer, venue, enabled_disciplines, slalom_gate_count
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                competition_date = excluded.competition_date,
                description = excluded.description,
                organizer = excluded.organizer,
                venue = excluded.venue,
                enabled_disciplines = excluded.enabled_disciplines,
                slalom_gate_count = excluded.slalom_gate_count
            """,
            (
                settings.name,
                settings.competition_date,
                settings.description,
                "\n".join(settings.organizers) if settings.organizers else settings.organizer,
                settings.venue,
                ",".join(settings.enabled_disciplines),
                settings.slalom_gate_count,
            ),
        )
        connection.execute("DELETE FROM competition_days")
        competition_days = settings.competition_dates or _normalize_competition_dates(settings.competition_date)
        connection.executemany(
            "INSERT INTO competition_days (day_order, competition_day) VALUES (?, ?)",
            [
                (index, competition_day)
                for index, competition_day in enumerate(competition_days, start=1)
            ],
        )
        connection.execute("DELETE FROM categories")
        connection.executemany(
            "INSERT INTO categories (boat_class, sex, age_group) VALUES (?, ?, ?)",
            [
                (category.boat_class, category.sex, category.age_group)
                for category in settings.categories
            ],
        )
        connection.commit()


def load_competition_settings(db_path: Path) -> CompetitionSettingsRecord:
    with sqlite3.connect(db_path) as connection:
        _ensure_competition_schema(connection)
        row = connection.execute(
            """
            SELECT name, competition_date, description, enabled_disciplines, slalom_gate_count
            , organizer, venue
            FROM competition_settings
            WHERE id = 1
            """
        ).fetchone()
        day_rows = connection.execute(
            "SELECT competition_day FROM competition_days ORDER BY day_order, id"
        ).fetchall()
        category_rows = connection.execute(
            "SELECT boat_class, sex, age_group FROM categories ORDER BY id"
        ).fetchall()

    if row is None:
        return CompetitionSettingsRecord(
            name="",
            competition_date="",
            competition_dates=[],
            description="",
            organizer="",
            organizers=[],
            venue="",
            enabled_disciplines=[],
            categories=[],
            slalom_gate_count=8,
        )

    categories = [
        Category(boat_class=boat_class, sex=sex, age_group=age_group)
        for boat_class, sex, age_group in category_rows
    ]
    disciplines = [value for value in row[3].split(",") if value]
    competition_dates = [day_row[0] for day_row in day_rows] or _normalize_competition_dates(row[1])
    organizers = [x.strip() for x in (row[5] or "").split("\n") if x.strip()]
    organizer_display = ", ".join(organizers) if organizers else (row[5] or "")
    return CompetitionSettingsRecord(
        name=row[0],
        competition_date=row[1],
        description=row[2],
        enabled_disciplines=disciplines,
        categories=categories,
        slalom_gate_count=row[4],
        competition_dates=competition_dates,
        organizer=organizer_display,
        organizers=organizers,
        venue=row[6],
    )


def _normalize_competition_dates(competition_date: str) -> list[str]:
    value = competition_date.strip()
    if not value:
        return []
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        return [value]
    return []


def _ensure_competition_schema(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(competition_settings)").fetchall()
    }
    if "organizer" not in columns:
        connection.execute(
            "ALTER TABLE competition_settings ADD COLUMN organizer TEXT NOT NULL DEFAULT ''"
        )
    if "venue" not in columns:
        connection.execute(
            "ALTER TABLE competition_settings ADD COLUMN venue TEXT NOT NULL DEFAULT ''"
        )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS competition_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_order INTEGER NOT NULL,
            competition_day TEXT NOT NULL
        )
        """
    )

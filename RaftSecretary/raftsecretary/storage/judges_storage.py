from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RequiredJudgeRecord:
    last_name: str
    first_name: str
    patronymic: str
    category: str

    @classmethod
    def empty(cls) -> "RequiredJudgeRecord":
        return cls(last_name="", first_name="", patronymic="", category="")

    @property
    def is_complete(self) -> bool:
        return all(
            [
                self.last_name.strip(),
                self.first_name.strip(),
                self.patronymic.strip(),
                self.category.strip(),
            ]
        )


@dataclass(frozen=True)
class JudgeRecord:
    last_name: str
    first_name: str
    patronymic: str
    category: str


@dataclass(frozen=True)
class JudgesRecord:
    chief_judge: RequiredJudgeRecord = field(default_factory=RequiredJudgeRecord.empty)
    chief_secretary: RequiredJudgeRecord = field(default_factory=RequiredJudgeRecord.empty)
    course_chief: RequiredJudgeRecord = field(default_factory=RequiredJudgeRecord.empty)
    judges: list[JudgeRecord] = field(default_factory=list)


def load_judges(db_path: Path) -> JudgesRecord:
    with sqlite3.connect(db_path) as connection:
        _ensure_judges_schema(connection)
        required_rows = connection.execute(
            """
            SELECT role_key, last_name, first_name, patronymic, category
            FROM required_judges
            """
        ).fetchall()
        required_map = {
            role_key: RequiredJudgeRecord(
                last_name=last_name,
                first_name=first_name,
                patronymic=patronymic,
                category=category,
            )
            for role_key, last_name, first_name, patronymic, category in required_rows
        }
        judge_rows = connection.execute(
            """
            SELECT last_name, first_name, patronymic, category
            FROM judges
            ORDER BY display_order, id
            """
        ).fetchall()

    return JudgesRecord(
        chief_judge=required_map.get("chief_judge", RequiredJudgeRecord.empty()),
        chief_secretary=required_map.get("chief_secretary", RequiredJudgeRecord.empty()),
        course_chief=required_map.get("course_chief", RequiredJudgeRecord.empty()),
        judges=[
            JudgeRecord(
                last_name=last_name,
                first_name=first_name,
                patronymic=patronymic,
                category=category,
            )
            for last_name, first_name, patronymic, category in judge_rows
        ],
    )


def save_judges(db_path: Path, record: JudgesRecord) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_judges_schema(connection)
        connection.execute("DELETE FROM required_judges")
        connection.execute("DELETE FROM judges")
        connection.executemany(
            """
            INSERT INTO required_judges (role_key, last_name, first_name, patronymic, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("chief_judge", record.chief_judge.last_name, record.chief_judge.first_name, record.chief_judge.patronymic, record.chief_judge.category),
                ("chief_secretary", record.chief_secretary.last_name, record.chief_secretary.first_name, record.chief_secretary.patronymic, record.chief_secretary.category),
                ("course_chief", record.course_chief.last_name, record.course_chief.first_name, record.course_chief.patronymic, record.course_chief.category),
            ],
        )
        connection.executemany(
            """
            INSERT INTO judges (display_order, last_name, first_name, patronymic, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (index, judge.last_name, judge.first_name, judge.patronymic, judge.category)
                for index, judge in enumerate(record.judges, start=1)
            ],
        )
        connection.commit()


def _ensure_judges_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS required_judges (
            role_key TEXT PRIMARY KEY,
            last_name TEXT NOT NULL DEFAULT '',
            first_name TEXT NOT NULL DEFAULT '',
            patronymic TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS judges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_order INTEGER NOT NULL,
            last_name TEXT NOT NULL DEFAULT '',
            first_name TEXT NOT NULL DEFAULT '',
            patronymic TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT ''
        );
        """
    )

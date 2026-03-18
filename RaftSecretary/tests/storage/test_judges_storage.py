import sqlite3
from pathlib import Path

from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.judges_storage import (
    JudgeRecord,
    JudgesRecord,
    RequiredJudgeRecord,
    load_judges,
    save_judges,
)


def test_save_and_load_judges(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)

    record = JudgesRecord(
        chief_judge=RequiredJudgeRecord(
            last_name="Иванов",
            first_name="Иван",
            patronymic="Иванович",
            category="Спортивный судья всероссийской категории",
        ),
        chief_secretary=RequiredJudgeRecord(
            last_name="Петрова",
            first_name="Анна",
            patronymic="Сергеевна",
            category="Спортивный судья первой категории",
        ),
        course_chief=RequiredJudgeRecord(
            last_name="Сидоров",
            first_name="Павел",
            patronymic="Олегович",
            category="Спортивный судья второй категории",
        ),
        judges=[
            JudgeRecord(
                last_name="Кузнецов",
                first_name="Дмитрий",
                patronymic="Андреевич",
                category="Спортивный судья третьей категории",
            ),
            JudgeRecord(
                last_name="Орлова",
                first_name="Мария",
                patronymic="Игоревна",
                category="Юный спортивный судья",
            ),
        ],
    )

    save_judges(db_path, record)
    loaded = load_judges(db_path)

    assert loaded == record


def test_load_judges_returns_empty_record_for_new_competition(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)

    loaded = load_judges(db_path)

    assert loaded.chief_judge == RequiredJudgeRecord.empty()
    assert loaded.chief_secretary == RequiredJudgeRecord.empty()
    assert loaded.course_chief == RequiredJudgeRecord.empty()
    assert loaded.judges == []


def test_load_judges_upgrades_legacy_database_without_judges_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE competition_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL DEFAULT '',
                competition_date TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                enabled_disciplines TEXT NOT NULL DEFAULT '',
                slalom_gate_count INTEGER NOT NULL DEFAULT 8
            )
            """
        )
        connection.commit()

    loaded = load_judges(db_path)

    assert loaded == JudgesRecord(
        chief_judge=RequiredJudgeRecord.empty(),
        chief_secretary=RequiredJudgeRecord.empty(),
        course_chief=RequiredJudgeRecord.empty(),
        judges=[],
    )

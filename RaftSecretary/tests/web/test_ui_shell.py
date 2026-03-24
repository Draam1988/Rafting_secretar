from pathlib import Path

from raftsecretary.storage.competition_storage import CompetitionSettingsRecord, save_competition_settings
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.judges_storage import (
    JudgeRecord,
    JudgesRecord,
    RequiredJudgeRecord,
    save_judges,
)
from raftsecretary.web.app import create_app


def test_home_page_shows_three_primary_actions_and_meta(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/")

    assert status == "200 OK"
    assert "RaftSecretary" in body
    assert "v.0." in body
    assert "Автор" in body
    assert "Открыть последнее соревнование" in body
    assert "Новое соревнование" in body
    assert ">event</a>" in body
    assert "УДАЛИТЬ" in body


def test_dashboard_page_shows_secretary_workspace_blocks(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Spring Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint", "slalom", "long_race"],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/dashboard?db=event.db")

    assert status == "200 OK"
    assert "Рабочий стол секретаря" in body
    assert "Соревнование" in body
    assert "Судьи" in body
    assert "Команды" in body
    assert "Спринт" in body
    assert "Параллельный спринт" in body
    assert "Слалом" in body
    assert "Длинная гонка" in body
    assert "Протоколы" in body


def test_dashboard_hides_disabled_disciplines(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Sprint Only",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/dashboard?db=event.db")

    assert status == "200 OK"
    assert "Спринт" in body
    assert "Параллельный спринт" not in body
    assert "Слалом" not in body
    assert "Длинная гонка" not in body


def test_dashboard_marks_judges_block_as_complete_when_roles_and_list_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_judges(
        db_path,
        JudgesRecord(
            chief_judge=RequiredJudgeRecord("Иванов", "Иван", "Иванович", "Спортивный судья всероссийской категории"),
            chief_secretary=RequiredJudgeRecord("Петрова", "Анна", "Сергеевна", "Спортивный судья первой категории"),
            course_chief=RequiredJudgeRecord("Сидоров", "Павел", "Олегович", "Спортивный судья второй категории"),
            judges=[JudgeRecord("Кузнецов", "Дмитрий", "Андреевич", "Спортивный судья третьей категории")],
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/dashboard?db=event.db")

    assert status == "200 OK"
    assert "Состав заполнен" in body


def test_protocols_page_lists_available_documents(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Spring Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export?db=event.db")

    assert status == "200 OK"
    assert "Реестр документов" in body
    assert "Итоговый протокол спринта" in body
    assert "/export/sprint-results?db=event.db" in body
    assert "Протокол многоборья" in body
    assert "/export/combined-results?db=event.db" in body

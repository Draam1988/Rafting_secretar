from pathlib import Path

from raftsecretary.domain.models import Category, Team
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.sprint_storage import load_sprint_entries
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_sprint_page_displays_all_teams_of_category_in_table(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 11, ["A1", "A2", "A3", "A4"]),
            Team("Beta", "Tver", "R4", "men", "U24", 12, ["B1", "B2", "B3", "B4"]),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "№ п/п" in body
    assert "Время первого старта" in body
    assert ">№<" in body
    assert "Субъект" in body
    assert "Штраф" in body
    assert "Место" in body
    assert "Alpha" in body
    assert "Beta" in body
    assert "Провести жеребьевку" in body
    assert "Пережеребить" in body


def test_sprint_save_endpoint_persists_table_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Storm", "Moscow", "R4", "men", "U24", 7, ["A1", "A2", "A3", "A4"]),
        ],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/sprint/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "row_1_team_name": "Storm",
            "row_1_start_order": "3",
            "row_1_start_time": "10:04",
            "row_1_base_time_seconds": "01:21",
            "row_1_behavior_penalty_seconds": "00:10",
            "row_1_status": "OK",
        },
    )

    entries = load_sprint_entries(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/sprint?db=event.db&category=R4%3Amen%3AU24&saved=1") in headers
    assert body == ""
    assert len(entries) == 1
    assert entries[0].start_order == 3
    assert entries[0].start_time == "10:04"
    assert entries[0].total_time_seconds == 91


def test_sprint_page_shows_collapsed_start_lineup_summary(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Storm", "Moscow", "R4", "men", "U16", 7, ["Иванов И.И.", "Петров П.П.", "Сидоров С.С.", "Смирнов С.С.", "Запасной З.З."]),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/sprint?db=event.db&category=R4:men:U16")

    assert status == "200 OK"
    assert "Иванов И.И. +3" in body
    assert "В старте" in body


def test_sprint_lineup_toggle_moves_member_between_start_and_reserve_lists(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Storm", "Moscow", "R4", "men", "U16", 7, ["Иванов И.И.", "Петров П.П.", "Сидоров С.С.", "Смирнов С.С.", "Запасной З.З."]),
        ],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/sprint/lineup",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U16",
            "lineup_target": "Storm|5|1",
        },
    )
    expanded_status, _, expanded_body = app.handle(
        "GET",
        "/sprint?db=event.db&category=R4:men:U16&open_team=Storm",
    )

    assert status == "303 See Other"
    assert ("Location", "/sprint?db=event.db&category=R4%3Amen%3AU16") in headers
    assert body == ""
    assert expanded_status == "200 OK"
    assert "В старте" in expanded_body
    assert "Вне старта" in expanded_body
    assert "Запасной З.З." in expanded_body
    assert "5/4" in expanded_body

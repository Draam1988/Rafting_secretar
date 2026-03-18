from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.domain.parallel_sprint import ParallelSprintHeatResult
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.long_race_storage import load_long_race_entries
from raftsecretary.storage.parallel_sprint_storage import save_parallel_sprint_heat
from raftsecretary.storage.slalom_storage import save_slalom_run
from raftsecretary.storage.sprint_storage import load_sprint_entries, save_sprint_entries
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_long_race_page_displays_operator_table(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["long_race"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 1, members=[
                TeamMember("A1", "2005", "Б/Р", "main"),
                TeamMember("A2", "2005", "Б/Р", "main"),
                TeamMember("A3", "2005", "Б/Р", "main"),
                TeamMember("A4", "2005", "Б/Р", "main"),
                TeamMember("AR", "2005", "Б/Р", "reserve"),
            ]),
            Team("Beta", "Tver", "R4", "men", "U24", 2, members=[
                TeamMember("B1", "2005", "Б/Р", "main"),
                TeamMember("B2", "2005", "Б/Р", "main"),
                TeamMember("B3", "2005", "Б/Р", "main"),
                TeamMember("B4", "2005", "Б/Р", "main"),
                TeamMember("BR", "2005", "Б/Р", "reserve"),
            ]),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/long-race?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "Стартовый протокол" in body
    assert "Сформировать стартовый порядок" in body
    assert "Промежуток" in body
    assert "№ п/п" in body
    assert "Время" in body
    assert "старта" in body
    assert "Состав" in body
    assert "Alpha" in body
    assert "Beta" in body
    assert "<option value=\"1\"" in body


def test_long_race_build_orders_by_combined_points_then_slalom_place_inside_parties(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint", "slalom", "long_race"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("Beta", "Tver", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("Gamma", "Perm", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("Alpha", 2, 45, 0, 0, "OK", "10:00"),
            SprintEntry("Beta", 3, 46, 0, 0, "OK", "10:02"),
            SprintEntry("Gamma", 1, 47, 0, 0, "OK", "10:04"),
        ],
    )
    save_parallel_sprint_heat(
        db_path,
        "R4:men:U24",
        "final_a",
        ParallelSprintHeatResult("Alpha", "left", 1, 80, 0, "OK"),
        ParallelSprintHeatResult("Gamma", "right", 2, 90, 0, "OK"),
    )
    save_slalom_run(db_path, "R4:men:U24", "Alpha", 1, 100, [0, 0])
    save_slalom_run(db_path, "R4:men:U24", "Gamma", 1, 110, [0, 0])
    save_slalom_run(db_path, "R4:men:U24", "Beta", 1, 120, [0, 0])
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/long-race/build",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "draw_start_time": "11:00",
            "draw_interval": "00:10",
            "row_1_team_name": "Alpha",
            "row_1_start_order": "2",
            "row_2_team_name": "Beta",
            "row_2_start_order": "2",
            "row_3_team_name": "Gamma",
            "row_3_start_order": "1",
        },
    )

    entries = load_long_race_entries(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/long-race?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert [entry.team_name for entry in entries] == ["Gamma", "Alpha", "Beta"]
    assert [entry.start_order for entry in entries] == [1, 2, 2]
    assert [entry.start_time for entry in entries] == ["11:00", "11:10", "11:10"]


def test_long_race_save_persists_table_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["long_race"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"])],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/long-race/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "row_1_team_name": "Alpha",
            "row_1_start_order": "3",
            "row_1_start_time": "12:00",
            "row_1_base_time_seconds": "30:00",
            "row_1_behavior_penalty_seconds": "00:10",
            "row_1_status": "OK",
        },
    )

    entries = load_long_race_entries(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/long-race?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert len(entries) == 1
    assert entries[0].start_order == 3
    assert entries[0].start_time == "12:00"
    assert entries[0].total_time_seconds == 1810


def test_long_race_status_persists_and_non_participant_fields_are_disabled(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["long_race"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"])],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/long-race/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "row_1_team_name": "Alpha",
            "row_1_start_order": "99",
            "row_1_start_time": "12:00",
            "row_1_base_time_seconds": "30:00",
            "row_1_behavior_penalty_seconds": "00:10",
            "row_1_status": "DNF",
        },
    )

    entries = load_long_race_entries(db_path, "R4:men:U24")
    assert status == "303 See Other"
    assert ("Location", "/long-race?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert entries[0].status == "Н/СТ"

    status, _, body = app.handle("GET", "/long-race?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert 'option value="99" selected' in body
    assert 'name="row_1_start_time"' in body
    assert 'name="row_1_start_time"' in body and "disabled" in body


def test_long_race_status_selection_survives_rerender(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["long_race"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"])],
    )
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/long-race/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "row_1_team_name": "Alpha",
            "row_1_start_order": "1",
            "row_1_start_time": "12:00",
            "row_1_base_time_seconds": "30:00",
            "row_1_behavior_penalty_seconds": "00:10",
            "row_1_status": "DNF",
        },
    )

    status, _, body = app.handle("GET", "/long-race?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert '<option value="DNF" selected' in body

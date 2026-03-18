from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.slalom_storage import load_slalom_runs
from raftsecretary.storage.sprint_storage import save_sprint_entries
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_slalom_page_shows_best_attempt_by_team(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["slalom"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=3,
        ),
    )
    save_teams(
        db_path,
        [
            Team(
                name="Alpha",
                region="Moscow",
                boat_class="R4",
                sex="men",
                age_group="U24",
                start_number=1,
                members=[
                    TeamMember("A1", "2008", "Б/Р", "main"),
                    TeamMember("A2", "2008", "Б/Р", "main"),
                    TeamMember("A3", "2008", "Б/Р", "main"),
                    TeamMember("A4", "2008", "Б/Р", "main"),
                    TeamMember("Reserve", "2008", "Б/Р", "reserve"),
                ],
            )
        ],
    )
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/slalom/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "team_name": "Alpha",
            "team_name": "Alpha",
            "attempt_1_base_time_seconds": "00:01:20",
            "attempt_1_gate_1": "0",
            "attempt_1_gate_2": "5",
            "attempt_1_gate_3": "50",
            "attempt_2_base_time_seconds": "",
            "attempt_2_gate_1": "0",
            "attempt_2_gate_2": "0",
            "attempt_2_gate_3": "0",
        },
    )
    app.handle(
        "POST",
        "/slalom/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "team_name": "Alpha",
            "team_name": "Alpha",
            "attempt_1_base_time_seconds": "00:01:20",
            "attempt_1_gate_1": "0",
            "attempt_1_gate_2": "5",
            "attempt_1_gate_3": "50",
            "attempt_2_base_time_seconds": "00:01:18",
            "attempt_2_gate_1": "0",
            "attempt_2_gate_2": "0",
            "attempt_2_gate_3": "0",
        },
    )

    status, _, body = app.handle("GET", "/slalom?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "Alpha" in body
    assert "1я попытка" in body
    assert "2я попытка" in body
    assert "состав команды" in body
    assert ">Состав</a>" in body
    assert "1в" in body
    assert "2в" in body
    assert "3в" in body
    assert "118" in body or "00:01:58" in body
    assert 'class="slalom-penalty-trigger">0</button>' in body
    assert 'type="hidden" form="slalom-1-1" name="attempt_1_gate_1" value="0"' in body


def test_slalom_save_endpoint_persists_run(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/slalom/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "team_name": "Alpha",
            "attempt_1_base_time_seconds": "00:01:20",
            "attempt_1_gate_1": "0",
            "attempt_1_gate_2": "5",
            "attempt_1_gate_3": "50",
            "attempt_2_base_time_seconds": "00:01:18",
            "attempt_2_gate_1": "0",
            "attempt_2_gate_2": "0",
            "attempt_2_gate_3": "0",
        },
    )

    runs = load_slalom_runs(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/slalom?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert len(runs) == 2
    assert runs[0].gate_penalties == [0, 5, 50]
    assert runs[1].gate_penalties == [0, 0, 0]


def test_slalom_page_builds_gate_columns_from_competition_settings(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["slalom"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=5,
        ),
    )
    save_teams(
        db_path,
        [Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"])],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/slalom?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "5в" in body
    assert "6в" not in body


def test_slalom_schedule_sets_start_times_for_both_attempts(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["slalom"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=3,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("Beta", "Tver", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
        ],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/slalom/schedule",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "attempt_1_start_time": "10:00:00",
            "attempt_1_interval_minutes": "2",
            "attempt_2_start_time": "10:30:00",
            "attempt_2_interval_minutes": "2",
        },
    )

    runs = load_slalom_runs(db_path, "R4:men:U24")
    by_key = {(run.team_name, run.attempt_number): run for run in runs}

    assert status == "303 See Other"
    assert ("Location", "/slalom?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert by_key[("Alpha", 1)].base_time_seconds == 36000
    assert by_key[("Beta", 1)].base_time_seconds == 36120
    assert by_key[("Alpha", 2)].base_time_seconds == 37800
    assert by_key[("Beta", 2)].base_time_seconds == 37920


def test_slalom_clear_removes_runs(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/slalom/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "team_name": "Alpha",
            "attempt_1_base_time_seconds": "00:01:20",
            "attempt_1_finish_time_seconds": "00:03:25",
            "attempt_1_gate_1": "0",
            "attempt_1_gate_2": "5",
            "attempt_1_gate_3": "50",
            "attempt_2_base_time_seconds": "",
            "attempt_2_gate_1": "0",
            "attempt_2_gate_2": "0",
            "attempt_2_gate_3": "0",
        },
    )

    status, headers, body = app.handle(
        "POST",
        "/slalom/clear",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
        },
    )

    assert status == "303 See Other"
    assert ("Location", "/slalom?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert load_slalom_runs(db_path, "R4:men:U24") == []


def test_slalom_schedule_uses_sprint_order_not_team_number(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "slalom"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=3,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 30, ["A1", "A2", "A3", "A4"]),
            Team("Beta", "Tver", "R4", "men", "U24", 10, ["B1", "B2", "B3", "B4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("Alpha", 1, 80, 0, 0, "OK"),
            SprintEntry("Beta", 2, 90, 0, 0, "OK"),
        ],
    )
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/slalom/schedule",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "attempt_1_start_time": "10:00:00",
            "attempt_1_interval_minutes": "2",
            "attempt_2_start_time": "10:30:00",
            "attempt_2_interval_minutes": "2",
        },
    )

    runs = load_slalom_runs(db_path, "R4:men:U24")
    by_key = {(run.team_name, run.attempt_number): run for run in runs}

    assert by_key[("Alpha", 1)].base_time_seconds == 36000
    assert by_key[("Beta", 1)].base_time_seconds == 36120

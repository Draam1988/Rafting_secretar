import sqlite3
from pathlib import Path

from raftsecretary.domain.models import Category, Team
from raftsecretary.storage.competition_storage import CompetitionSettingsRecord, save_competition_settings
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.team_storage import load_teams, save_teams
from raftsecretary.web.app import create_app


def test_team_delete_confirmation_page_is_available(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [Team(name="Storm", region="Moscow", boat_class="R4", sex="men", age_group="U24", start_number=1)],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/teams/delete?db=event.db&category=R4%3Amen%3AU24&start_number=1")

    assert status == "200 OK"
    assert "Удалить команду" in body
    assert "Storm" in body


def test_team_delete_endpoint_removes_team(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [Team(name="Storm", region="Moscow", boat_class="R4", sex="men", age_group="U24", start_number=1)],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/teams/delete",
        form_data={"db": "event.db", "boat_class": "R4", "sex": "men", "age_group": "U24", "start_number": "1", "confirm": "yes"},
    )

    assert status == "303 See Other"
    assert ("Location", "/teams?db=event.db") in headers
    assert body == ""
    assert load_teams(db_path) == []


def test_team_delete_targets_exact_team_record_even_with_duplicate_numbers(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team(name="Storm", region="Moscow", boat_class="R4", sex="men", age_group="U24", start_number=7),
            Team(name="Wave", region="Perm", boat_class="R4", sex="men", age_group="U24", start_number=7),
        ],
    )
    with sqlite3.connect(db_path) as connection:
        team_rows = connection.execute(
            "SELECT id, name FROM teams ORDER BY id"
        ).fetchall()
    wave_id = next(team_id for team_id, name in team_rows if name == "Wave")
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", f"/teams/delete?db=event.db&team_id={wave_id}")

    assert status == "200 OK"
    assert "Wave" in body
    assert "Storm" not in body

    status, headers, response_body = app.handle(
        "POST",
        "/teams/delete",
        form_data={"db": "event.db", "team_id": str(wave_id), "confirm": "yes"},
    )

    remaining = load_teams(db_path)

    assert status == "303 See Other"
    assert ("Location", "/teams?db=event.db") in headers
    assert response_body == ""
    assert [team.name for team in remaining] == ["Storm"]


def test_repeated_identical_team_save_does_not_create_duplicate(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)
    form_data = {
        "db": "event.db",
        "name": "Storm",
        "region": "Moscow",
        "club": "Rapid",
        "representative_full_name": "Иванов Иван",
        "boat_class": "R4",
        "sex": "men",
        "age_group": "U24",
        "start_number": "7",
        "member_1_full_name": "A1",
        "member_1_birth_date": "2008",
        "member_1_rank": "Б/Р",
        "member_1_role": "main",
    }

    first_status, _, _ = app.handle("POST", "/teams/add", form_data=form_data)
    second_status, second_headers, second_body = app.handle("POST", "/teams/add", form_data=form_data)

    teams = load_teams(db_path)

    assert first_status == "303 See Other"
    assert second_status == "303 See Other"
    assert ("Location", "/teams?db=event.db&open_category=R4%3Amen%3AU24#category-R4-men-U24") in second_headers
    assert second_body == ""
    assert len(teams) == 1
    assert teams[0].name == "Storm"

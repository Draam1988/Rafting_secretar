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

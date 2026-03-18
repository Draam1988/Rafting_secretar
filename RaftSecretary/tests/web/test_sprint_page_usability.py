from pathlib import Path

from raftsecretary.domain.models import Category, Team
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_sprint_page_shows_available_categories_and_teams(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
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

    status, _, body = app.handle("GET", "/sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "R4:men:U24" in body
    assert "Alpha" in body
    assert "Beta" in body
    assert "Стартовый протокол" in body
    assert "Состав" in body

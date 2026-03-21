from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_settings_page_displays_saved_competition_settings(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Spring Cup",
            competition_date="2026-05-10",
            description="Test river",
            organizer="Минспорт",
            venue="р. Белая",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[],
            slalom_gate_count=9,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/settings?db=event.db")

    assert status == "200 OK"
    assert "Spring Cup" in body
    assert "2026-05-10" in body
    assert "Минспорт" in body
    assert "р. Белая" in body
    assert "Параллельный спринт" in body
    assert "9" in body
    assert "Дисциплины" in body
    assert "Категории" in body
    assert "R4 Юниоры до 24 лет" in body
    assert "2 выбрано" in body


def test_teams_page_displays_saved_teams(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[
                Category("R4", "men", "U24"),
                Category("R6", "women", "U20"),
            ],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team(
                name="Storm",
                region="Moscow",
                club="Storm Club",
                representative_full_name="Иванов Иван Иванович",
                boat_class="R4",
                sex="men",
                age_group="U24",
                start_number=1,
                members=[
                    TeamMember("A1", "2005-01-01", "КМС", "main"),
                    TeamMember("A2", "2005-02-02", "1 разряд", "main"),
                    TeamMember("A3", "2005-03-03", "1 разряд", "main"),
                    TeamMember("A4", "2005-04-04", "2 разряд", "main"),
                    TeamMember("A5", "2006-05-05", "2 разряд", "reserve"),
                ],
            )
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/teams?db=event.db")

    assert status == "200 OK"
    assert "R4 Юниоры до 24 лет" in body
    assert "R6 Юниорки до 20 лет" in body
    assert "+ Добавить команду" in body
    assert "Субъект РФ" in body
    assert "Storm" in body
    assert "Moscow" in body
    assert "Storm Club" in body
    assert "Иванов Иван Иванович" in body
    assert "№" in body
    assert "Год рождения" in body
    assert "Б/Р" in body
    assert "Свой вариант" not in body

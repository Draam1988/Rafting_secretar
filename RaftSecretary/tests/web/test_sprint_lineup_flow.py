from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.web.app import create_app


def test_sprint_page_shows_compact_start_lineup_summary(tmp_path: Path) -> None:
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
    save_team = Team(
        name="Alpha",
        region="Moscow",
        boat_class="R4",
        sex="men",
        age_group="U16",
        start_number=1,
        members=[
            TeamMember("Иванов Илья Андреевич", "2011", "Б/Р", "main"),
            TeamMember("Петров Данил Игоревич", "2012", "Б/Р", "main"),
            TeamMember("Сидоров Максим Сергеевич", "2013", "Б/Р", "main"),
            TeamMember("Егоров Егор Олегович", "2014", "Б/Р", "main"),
            TeamMember("Резерв Артем Олегович", "2012", "Б/Р", "reserve"),
        ],
    )
    from raftsecretary.storage.team_storage import save_teams

    save_teams(db_path, [save_team])
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/sprint?db=event.db&category=R4:men:U16")

    assert status == "200 OK"
    assert "Иванов Илья Андреевич +3" in body
    assert "В старте" in body
    assert "Вне старта" in body


def test_sprint_lineup_toggle_moves_member_out_and_back(tmp_path: Path) -> None:
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
    from raftsecretary.storage.team_storage import save_teams

    save_teams(
        db_path,
        [
            Team(
                name="Alpha",
                region="Moscow",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=1,
                members=[
                    TeamMember("Иванов Илья Андреевич", "2011", "Б/Р", "main"),
                    TeamMember("Петров Данил Игоревич", "2012", "Б/Р", "main"),
                    TeamMember("Сидоров Максим Сергеевич", "2013", "Б/Р", "main"),
                    TeamMember("Егоров Егор Олегович", "2014", "Б/Р", "main"),
                    TeamMember("Резерв Артем Олегович", "2012", "Б/Р", "reserve"),
                ],
            )
        ],
    )
    app = create_app(tmp_path)

    status, headers, _ = app.handle(
        "POST",
        "/sprint/lineup",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U16",
            "team_name": "Alpha",
            "member_full_name": "Петров Данил Игоревич",
            "active": "0",
        },
    )

    assert status == "303 See Other"
    assert ("Location", "/sprint?db=event.db&category=R4%3Amen%3AU16") in headers

    status, _, body = app.handle("GET", "/sprint?db=event.db&category=R4:men:U16")

    assert status == "200 OK"
    assert "Состав 3/4" in body
    assert "Петров Данил Игоревич" in body
    assert "вернуть" in body

    status, headers, _ = app.handle(
        "POST",
        "/sprint/lineup",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U16",
            "team_name": "Alpha",
            "member_full_name": "Петров Данил Игоревич",
            "active": "1",
        },
    )

    assert status == "303 See Other"
    assert ("Location", "/sprint?db=event.db&category=R4%3Amen%3AU16") in headers

    status, _, body = app.handle("GET", "/sprint?db=event.db&category=R4:men:U16")

    assert status == "200 OK"
    assert "Состав 4/4" in body

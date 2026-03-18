from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.domain.points import points_for_place
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.judges_storage import (
    JudgesRecord,
    RequiredJudgeRecord,
    save_judges,
)
from raftsecretary.storage.long_race_storage import (
    save_long_race_entries,
    save_long_race_lineup_flags,
)
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_long_race_results_protocol_is_listed_in_export_registry(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Spring Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["long_race"],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол длинной гонки" in body
    assert "/export/long-race-results?db=event.db" in body


def test_long_race_results_protocol_renders_header_table_and_party_order(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Первенство ЮФО",
            competition_date="2026-03-27",
            description="",
            organizer="Федерация рафтинга ЮФО",
            venue="Река Белая",
            enabled_disciplines=["long_race"],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
            competition_dates=["2026-03-27", "2026-03-28"],
        ),
    )
    save_judges(
        db_path,
        JudgesRecord(
            chief_judge=RequiredJudgeRecord("Иванов", "Иван", "Иванович", "Спортивный судья всероссийской категории"),
            chief_secretary=RequiredJudgeRecord("Петров", "Павел", "Павлович", "Спортивный судья первой категории"),
        ),
    )
    save_teams(
        db_path,
        [
            Team(
                name="Шторм",
                region="Краснодарский край",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=7,
                members=[
                    TeamMember("Иванов Илья", "2011", "Б/Р", "main"),
                    TeamMember("Петров Данил", "2012", "Б/Р", "main"),
                    TeamMember("Сидоров Максим", "2013", "Б/Р", "main"),
                    TeamMember("Егоров Егор", "2014", "Б/Р", "main"),
                    TeamMember("Запасной Артем", "2012", "Б/Р", "reserve"),
                ],
            ),
            Team(
                name="Каньон",
                region="Адыгея",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=9,
                members=[
                    TeamMember("К1", "2011", "Б/Р", "main"),
                    TeamMember("К2", "2012", "Б/Р", "main"),
                    TeamMember("К3", "2013", "Б/Р", "main"),
                    TeamMember("К4", "2014", "Б/Р", "main"),
                    TeamMember("К5", "2012", "Б/Р", "reserve"),
                ],
            ),
        ],
    )
    save_long_race_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 2, 300, 0, 0, "OK", "11:10"),
            SprintEntry("Каньон", 1, 330, 0, 0, "OK", "11:00"),
        ],
    )
    save_long_race_lineup_flags(
        db_path,
        "R4:men:U16",
        {
            "Шторм": {1: True, 2: True, 3: True, 4: False, 5: True},
            "Каньон": {1: True, 2: True, 3: True, 4: True, 5: False},
        },
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/long-race-results?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол" in body
    assert "Длинная гонка" in body
    assert "Федерация рафтинга ЮФО" in body
    assert "Река Белая" in body
    assert "R4 Мужчины U16" in body
    assert "Каньон" in body
    assert "Шторм" in body
    assert "11:00" in body
    assert "11:10" in body
    assert "05:00" in body
    assert "05:30" in body
    assert "Иванов Илья, 2011, Б/Р<br />Петров Данил, 2012, Б/Р<br />Сидоров Максим, 2013, Б/Р<br />Запасной Артем, 2012, Б/Р" in body
    assert "Егоров Егор" not in body


def test_long_race_results_protocol_gives_zero_points_to_non_participant(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Первенство ЮФО",
            competition_date="2026-03-27",
            description="",
            enabled_disciplines=["long_race"],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
            competition_dates=["2026-03-27"],
        ),
    )
    save_teams(
        db_path,
        [
            Team("Шторм", "Краснодарский край", "R4", "men", "U16", 7, ["А1", "А2", "А3", "А4"]),
            Team("Каньон", "Адыгея", "R4", "men", "U16", 9, ["К1", "К2", "К3", "К4"]),
        ],
    )
    save_long_race_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 1, 300, 0, 0, "OK", "11:00"),
            SprintEntry("Каньон", 99, 0, 0, 0, "Н/СТ", ""),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/long-race-results?db=event.db")

    assert status == "200 OK"
    assert ">1<" in body
    assert f">{points_for_place('long_race', 1)}<" in body
    assert ">0<" in body
    assert ">н/у<" in body

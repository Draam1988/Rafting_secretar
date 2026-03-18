from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
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
from raftsecretary.storage.sprint_storage import (
    save_sprint_entries,
    save_sprint_lineup_flags,
)
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_sprint_results_protocol_renders_header_and_category_tables(tmp_path: Path) -> None:
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
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U16"), Category("R4", "women", "U16")],
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
                name="Волна",
                region="Ростовская область",
                boat_class="R4",
                sex="women",
                age_group="U16",
                start_number=3,
                members=[
                    TeamMember("Анна Первая", "2011", "Б/Р", "main"),
                    TeamMember("Анна Вторая", "2012", "Б/Р", "main"),
                    TeamMember("Анна Третья", "2013", "Б/Р", "main"),
                    TeamMember("Анна Четвертая", "2014", "Б/Р", "main"),
                    TeamMember("Анна Запасная", "2012", "Б/Р", "reserve"),
                ],
            ),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 1, 45, 0, 0, "OK", "10:00"),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:women:U16",
        [
            SprintEntry("Волна", 2, 50, 0, 10, "DNF", "10:10"),
        ],
    )
    save_sprint_lineup_flags(
        db_path,
        "R4:men:U16",
        {"Шторм": {1: True, 2: True, 3: True, 4: False, 5: True}},
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/sprint-results?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол" in body
    assert "Спринт" in body
    assert "Федерация рафтинга ЮФО" in body
    assert "Река Белая" in body
    assert "Первенство ЮФО" in body
    assert "2026-03-27" in body
    assert "R4 Мужчины U16" in body
    assert "R4 Женщины U16" in body
    assert "Шторм" in body
    assert "Волна" in body
    assert "Главный судья" in body
    assert "Иванов Иван Иванович" in body
    assert "Главный секретарь" in body
    assert "Петров Павел Павлович" in body
    assert "Примечание" not in body


def test_sprint_results_protocol_uses_start_lineup_places_points_and_status_note(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Первенство ЮФО",
            competition_date="2026-03-27",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
            competition_dates=["2026-03-27"],
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
    save_sprint_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 2, 45, 0, 0, "OK", "10:00"),
            SprintEntry("Каньон", 1, 48, 0, 10, "DNS", "10:02"),
        ],
    )
    save_sprint_lineup_flags(
        db_path,
        "R4:men:U16",
        {
            "Шторм": {1: True, 2: True, 3: True, 4: False, 5: True},
            "Каньон": {1: True, 2: True, 3: True, 4: True, 5: False},
        },
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/sprint-results?db=event.db")

    assert status == "200 OK"
    assert "Иванов Илья, 2011, Б/Р<br />Петров Данил, 2012, Б/Р<br />Сидоров Максим, 2013, Б/Р<br />Запасной Артем, 2012, Б/Р" in body
    assert "Егоров Егор" not in body
    assert "10:00" in body
    assert "00:45" in body
    assert "00:00" in body
    assert ">2<" in body
    assert ">100<" in body

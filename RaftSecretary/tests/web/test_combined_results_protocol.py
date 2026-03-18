from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.domain.parallel_sprint import ParallelSprintHeatResult
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
from raftsecretary.storage.long_race_storage import save_long_race_entries
from raftsecretary.storage.parallel_sprint_storage import save_parallel_sprint_heat
from raftsecretary.storage.slalom_storage import save_slalom_run
from raftsecretary.storage.sprint_storage import save_sprint_entries
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_combined_results_protocol_renders_one_page_category_table(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Первенство ЮФО",
            competition_date="2026-03-27",
            description="",
            organizer="Федерация рафтинга России",
            venue="Река Белая",
            enabled_disciplines=["sprint", "parallel_sprint", "slalom", "long_race"],
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
                ],
            ),
            Team(
                name="Рапид",
                region="Республика Крым",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=10,
                members=[
                    TeamMember("Р1", "2011", "Б/Р", "main"),
                    TeamMember("Р2", "2012", "Б/Р", "main"),
                    TeamMember("Р3", "2013", "Б/Р", "main"),
                    TeamMember("Р4", "2014", "Б/Р", "main"),
                ],
            ),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 2, 45, 0, 0, "OK", "10:00"),
            SprintEntry("Каньон", 1, 50, 0, 0, "OK", "10:02"),
            SprintEntry("Рапид", 3, 55, 0, 0, "OK", "10:04"),
        ],
    )
    save_parallel_sprint_heat(
        db_path,
        "R4:men:U16",
        "final_a",
        ParallelSprintHeatResult("Шторм", "left", 1, 80, 0, "OK"),
        ParallelSprintHeatResult("Каньон", "right", 2, 90, 0, "OK"),
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Шторм",
        1,
        10 * 3600,
        [0, 5],
        finish_time_seconds=10 * 3600 + 60,
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Каньон",
        1,
        10 * 3600,
        [0, 0],
        finish_time_seconds=10 * 3600 + 55,
    )
    save_long_race_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 1, 300, 0, 0, "OK"),
            SprintEntry("Каньон", 2, 320, 0, 0, "OK"),
            SprintEntry("Рапид", 3, 340, 0, 0, "OK"),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/combined-results?db=event.db")

    assert status == "200 OK"
    assert "Протокол многоборья" in body
    assert "R4 Мужчины U16" in body
    assert "Спринт" in body
    assert "H2H" in body
    assert "Слалом" in body
    assert "Длинная гонка" in body
    assert "Многоборье" in body
    assert "Федерация рафтинга России" in body
    assert "Главный судья" in body


def test_combined_results_protocol_shows_place_and_points_in_two_lines(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Первенство ЮФО",
            competition_date="2026-03-27",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint", "slalom", "long_race"],
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
                    TeamMember("Петров Данил", "2012", "1 юношеский", "main"),
                    TeamMember("Сидоров Максим", "2013", "2 разряд", "main"),
                    TeamMember("Егоров Егор", "2014", "3 разряд", "main"),
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
                ],
            ),
            Team(
                name="Рапид",
                region="Республика Крым",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=10,
                members=[
                    TeamMember("Р1", "2011", "Б/Р", "main"),
                    TeamMember("Р2", "2012", "Б/Р", "main"),
                    TeamMember("Р3", "2013", "Б/Р", "main"),
                    TeamMember("Р4", "2014", "Б/Р", "main"),
                ],
            ),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 2, 45, 0, 0, "OK", "10:00"),
            SprintEntry("Каньон", 1, 50, 0, 0, "OK", "10:02"),
            SprintEntry("Рапид", 3, 55, 0, 0, "OK", "10:04"),
        ],
    )
    save_parallel_sprint_heat(
        db_path,
        "R4:men:U16",
        "final_a",
        ParallelSprintHeatResult("Шторм", "left", 1, 80, 0, "OK"),
        ParallelSprintHeatResult("Каньон", "right", 2, 90, 0, "OK"),
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Шторм",
        1,
        10 * 3600,
        [0, 5],
        finish_time_seconds=10 * 3600 + 60,
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Каньон",
        1,
        10 * 3600,
        [0, 0],
        finish_time_seconds=10 * 3600 + 55,
    )
    save_long_race_entries(
        db_path,
        "R4:men:U16",
        [
            SprintEntry("Шторм", 1, 300, 0, 0, "OK"),
            SprintEntry("Каньон", 2, 320, 0, 0, "OK"),
            SprintEntry("Рапид", 3, 340, 0, 0, "OK"),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/combined-results?db=event.db")

    assert status == "200 OK"
    assert "Запасной Артем" not in body
    assert "Иванов Илья, 2011, Б/Р<br />Петров Данил, 2012, 1 юношеский" in body
    assert "<td class=\"col-discipline discipline-cell\">1<br /><span class=\"discipline-points\">100</span></td>" in body
    assert "2<br /><span class=\"discipline-points\">95</span>" in body
    assert "1<br /><span class=\"discipline-points\">200</span>" in body
    assert "3<br /><span class=\"discipline-points\">180</span>" in body
    assert "1<br /><span class=\"discipline-points\">300</span>" in body
    assert "1<br /><span class=\"discipline-points\">400</span>" in body
    assert "1<br /><span class=\"discipline-points\">985</span>" in body

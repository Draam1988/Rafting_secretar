from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.domain.points import points_for_place
from raftsecretary.domain.parallel_sprint import ParallelSprintHeatResult
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
from raftsecretary.storage.parallel_sprint_storage import (
    ParallelSprintHeatMeta,
    save_parallel_sprint_heat,
    save_parallel_sprint_heat_meta,
    save_parallel_sprint_lineup_flags,
)
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_parallel_sprint_results_protocol_is_listed_in_export_registry(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Spring Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["parallel_sprint"],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол H2H" in body
    assert "/export/parallel-sprint-results?db=event.db" in body


def test_parallel_sprint_results_protocol_renders_places_points_and_active_lineup(tmp_path: Path) -> None:
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
            enabled_disciplines=["parallel_sprint"],
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
                    TeamMember("Петров Данил", "2012", "1 юношеский", "main"),
                    TeamMember("Сидоров Максим", "2013", "2 разряд", "main"),
                    TeamMember("Егоров Егор", "2014", "3 разряд", "main"),
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
                name="Рубеж",
                region="Республика Адыгея",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=4,
                members=[
                    TeamMember("Р1", "2011", "Б/Р", "main"),
                    TeamMember("Р2", "2012", "Б/Р", "main"),
                    TeamMember("Р3", "2013", "Б/Р", "main"),
                    TeamMember("Р4", "2014", "Б/Р", "main"),
                ],
            ),
            Team(
                name="Волейбол",
                region="Горячий Ключ",
                boat_class="R4",
                sex="men",
                age_group="U16",
                start_number=34,
                members=[
                    TeamMember("В1", "2011", "Б/Р", "main"),
                    TeamMember("В2", "2012", "Б/Р", "main"),
                    TeamMember("В3", "2013", "Б/Р", "main"),
                    TeamMember("В4", "2014", "Б/Р", "main"),
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
                    TeamMember("Ра1", "2011", "Б/Р", "main"),
                    TeamMember("Ра2", "2012", "Б/Р", "main"),
                    TeamMember("Ра3", "2013", "Б/Р", "main"),
                    TeamMember("Ра4", "2014", "Б/Р", "main"),
                ],
            ),
        ],
    )
    save_parallel_sprint_lineup_flags(
        db_path,
        "R4:men:U16",
        {"Шторм": {1: True, 2: True, 3: False, 4: True, 5: True}},
    )
    save_parallel_sprint_heat(
        db_path,
        "R4:men:U16",
        "final_a",
        ParallelSprintHeatResult("Шторм", "left", 1, 80, 0, "OK"),
        ParallelSprintHeatResult("Каньон", "right", 2, 90, 1, "OK"),
    )
    save_parallel_sprint_heat_meta(
        db_path,
        "R4:men:U16",
        ParallelSprintHeatMeta("final_a", "", 80, 0, 40, 50, "Шторм"),
    )
    save_parallel_sprint_heat(
        db_path,
        "R4:men:U16",
        "final_b",
        ParallelSprintHeatResult("Рубеж", "left", 4, 85, 0, "OK"),
        ParallelSprintHeatResult("Волейбол", "right", 34, 95, 0, "OK"),
    )
    save_parallel_sprint_heat_meta(
        db_path,
        "R4:men:U16",
        ParallelSprintHeatMeta("final_b", "", 35, 50, 45, 50, "Рубеж"),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/parallel-sprint-results?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол" in body
    assert "Дисциплина: H2H" in body
    assert "R4 Мужчины U16" in body
    assert "Федерация рафтинга России" in body
    assert "Главный судья" in body
    assert "Иванов Илья, 2011, Б/Р<br />Петров Данил, 2012, 1 юношеский<br />Егоров Егор, 2014, 3 разряд<br />Запасной Артем, 2012, Б/Р" in body
    assert "Сидоров Максим" not in body
    assert ">00:40<" in body
    assert ">00:50<" in body
    assert ">01:30<" in body
    assert f">{points_for_place('parallel_sprint', 1)}<" in body
    assert f">{points_for_place('parallel_sprint', 2)}<" in body
    assert f">{points_for_place('parallel_sprint', 3)}<" in body
    assert f">{points_for_place('parallel_sprint', 4)}<" in body
    assert f">{points_for_place('parallel_sprint', 5)}<" in body
    assert ">1<" in body
    assert ">2<" in body
    assert ">3<" in body
    assert ">4<" in body
    assert ">5<" in body

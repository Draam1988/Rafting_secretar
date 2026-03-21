from pathlib import Path

from raftsecretary.domain.models import Category, Team, TeamMember
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
from raftsecretary.storage.slalom_storage import (
    save_slalom_lineup_flags,
    save_slalom_run,
)
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_slalom_results_protocol_is_listed_in_export_registry(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Spring Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["slalom"],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол слалома" in body
    assert "/export/slalom-results?db=event.db" in body


def test_slalom_results_protocol_renders_attempts_best_result_places_and_active_lineup(
    tmp_path: Path,
) -> None:
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
            enabled_disciplines=["slalom"],
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
        ],
    )
    save_slalom_lineup_flags(
        db_path,
        "R4:men:U16",
        {"Шторм": {1: True, 2: False, 3: True, 4: True, 5: True}},
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Шторм",
        1,
        10 * 3600,
        [0, 5, 0],
        finish_time_seconds=10 * 3600 + 65,
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Шторм",
        2,
        11 * 3600,
        [0, 0, 0],
        finish_time_seconds=11 * 3600 + 70,
    )
    save_slalom_run(
        db_path,
        "R4:men:U16",
        "Каньон",
        1,
        10 * 3600,
        [0, 0, 0],
        finish_time_seconds=10 * 3600 + 60,
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export/slalom-results?db=event.db")

    assert status == "200 OK"
    assert "Итоговый протокол" in body
    assert "Дисциплина: Слалом" in body
    assert "R4 Юноши до 16 лет" in body
    assert "Федерация рафтинга России" in body
    assert "Главный судья" in body
    assert "старт" in body
    assert "финиш" in body
    assert "1в" in body
    assert "8в" in body
    assert "итог" in body
    assert "лучшая" in body
    assert "Иванов Илья, 2011, Б/Р<br />Сидоров Максим, 2013, 2р<br />Егоров Егор, 2014, 3р<br />Запасной Артем, 2012, Б/Р" in body
    assert "Петров Данил" not in body
    assert "10:00:00" in body
    assert "10:01:05" in body
    assert "11:00:00" in body
    assert "11:01:10" in body
    assert ">01:10<" in body
    assert ">01:00<" in body
    assert ">1<" in body
    assert ">2<" in body

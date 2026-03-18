from pathlib import Path

from raftsecretary.domain.models import Team, TeamMember
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.team_storage import load_teams, save_teams


def test_save_and_load_teams_with_athletes(tmp_path: Path) -> None:
    db_path = tmp_path / "teams.db"
    create_competition_db(db_path)

    teams = [
        Team(
            name="Storm",
            region="Moscow",
            boat_class="R4",
            sex="men",
            age_group="U24",
            start_number=1,
            athletes=["A1", "A2", "A3", "A4"],
        ),
        Team(
            name="River",
            region="Tver",
            boat_class="R6",
            sex="women",
            age_group="U20",
            start_number=2,
            athletes=["B1", "B2", "B3", "B4", "B5", "B6"],
        ),
    ]

    save_teams(db_path, teams)
    loaded = load_teams(db_path)

    assert loaded == teams


def test_save_teams_replaces_previous_team_list(tmp_path: Path) -> None:
    db_path = tmp_path / "replace.db"
    create_competition_db(db_path)

    save_teams(
        db_path,
        [
            Team(
                name="Old",
                region="OldRegion",
                boat_class="R4",
                sex="men",
                age_group="U24",
                start_number=1,
                athletes=["A", "B", "C", "D"],
            )
        ],
    )
    save_teams(
        db_path,
        [
            Team(
                name="New",
                region="NewRegion",
                boat_class="R4",
                sex="women",
                age_group="U20",
                start_number=7,
                athletes=["E", "F", "G", "H"],
            )
        ],
    )

    loaded = load_teams(db_path)

    assert [team.name for team in loaded] == ["New"]


def test_save_and_load_teams_with_detailed_members(tmp_path: Path) -> None:
    db_path = tmp_path / "detailed.db"
    create_competition_db(db_path)

    teams = [
        Team(
            name="Волна",
            region="Краснодарский край",
            club="КК Рафт",
            representative_full_name="Иванов Иван Иванович",
            boat_class="R4",
            sex="men",
            age_group="U24",
            start_number=10,
            members=[
                TeamMember("А1", "2005-01-01", "КМС", "main"),
                TeamMember("А2", "2005-02-02", "1 разряд", "main"),
                TeamMember("А3", "2005-03-03", "1 разряд", "main"),
                TeamMember("А4", "2005-04-04", "2 разряд", "main"),
                TeamMember("Запасной", "2006-05-05", "2 разряд", "reserve"),
            ],
        )
    ]

    save_teams(db_path, teams)
    loaded = load_teams(db_path)

    assert loaded == teams

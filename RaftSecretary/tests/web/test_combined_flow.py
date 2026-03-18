from pathlib import Path

from raftsecretary.domain.models import Category, Team
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.domain.status_rules import STATUS_OK
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.long_race_storage import save_long_race_entries
from raftsecretary.storage.parallel_sprint_storage import save_parallel_sprint_heat
from raftsecretary.storage.slalom_storage import save_slalom_run
from raftsecretary.storage.sprint_storage import save_sprint_entries
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.domain.parallel_sprint import ParallelSprintHeatResult
from raftsecretary.web.app import create_app


def test_combined_page_shows_total_points_by_team(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint", "slalom", "long_race"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=3,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("Beta", "Tver", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("Alpha", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("Beta", 2, 81, 0, 0, STATUS_OK),
        ],
    )
    save_parallel_sprint_heat(
        db_path,
        "R4:men:U24",
        "final_a",
        ParallelSprintHeatResult("Alpha", "left", 1, 120, 0, STATUS_OK),
        ParallelSprintHeatResult("Beta", "right", 2, 125, 0, STATUS_OK),
    )
    save_slalom_run(db_path, "R4:men:U24", "Alpha", 1, 120, [0, 0, 0])
    save_slalom_run(db_path, "R4:men:U24", "Beta", 1, 125, [0, 0, 0])
    save_long_race_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("Alpha", 1, 3600, 0, 0, STATUS_OK),
            SprintEntry("Beta", 2, 3610, 0, 0, STATUS_OK),
        ],
    )

    app = create_app(tmp_path)
    status, _, body = app.handle("GET", "/combined?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "Alpha" in body
    assert "Beta" in body
    assert "1000" in body
    assert "950" in body


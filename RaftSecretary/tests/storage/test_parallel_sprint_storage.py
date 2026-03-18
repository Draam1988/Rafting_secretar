from pathlib import Path

from raftsecretary.domain.parallel_sprint import ParallelSprintHeatResult
from raftsecretary.domain.status_rules import STATUS_OK
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.parallel_sprint_storage import (
    load_parallel_sprint_heats,
    save_parallel_sprint_heat,
)


def test_save_and_load_parallel_sprint_heats(tmp_path: Path) -> None:
    db_path = tmp_path / "parallel.db"
    create_competition_db(db_path)

    save_parallel_sprint_heat(
        db_path=db_path,
        category_key="R4:men:U24",
        round_name="semifinal_1",
        left=ParallelSprintHeatResult("Alpha", "left", 1, 120, 0, STATUS_OK),
        right=ParallelSprintHeatResult("Beta", "right", 2, 125, 0, STATUS_OK),
    )

    heats = load_parallel_sprint_heats(db_path, "R4:men:U24")

    assert len(heats) == 1
    assert heats[0][0] == "semifinal_1"
    assert heats[0][1].team_name == "Alpha"
    assert heats[0][2].team_name == "Beta"


def test_saving_same_round_replaces_existing_heat(tmp_path: Path) -> None:
    db_path = tmp_path / "replace.db"
    create_competition_db(db_path)

    save_parallel_sprint_heat(
        db_path=db_path,
        category_key="R4:men:U24",
        round_name="semifinal_1",
        left=ParallelSprintHeatResult("OldA", "left", 1, 120, 0, STATUS_OK),
        right=ParallelSprintHeatResult("OldB", "right", 2, 125, 0, STATUS_OK),
    )
    save_parallel_sprint_heat(
        db_path=db_path,
        category_key="R4:men:U24",
        round_name="semifinal_1",
        left=ParallelSprintHeatResult("NewA", "left", 1, 118, 0, STATUS_OK),
        right=ParallelSprintHeatResult("NewB", "right", 2, 121, 0, STATUS_OK),
    )

    heats = load_parallel_sprint_heats(db_path, "R4:men:U24")

    assert len(heats) == 1
    assert heats[0][1].team_name == "NewA"
    assert heats[0][2].team_name == "NewB"


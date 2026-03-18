from pathlib import Path

from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.slalom_storage import load_slalom_runs, save_slalom_run


def test_save_and_load_slalom_runs(tmp_path: Path) -> None:
    db_path = tmp_path / "slalom.db"
    create_competition_db(db_path)

    save_slalom_run(
        db_path=db_path,
        category_key="R4:men:U24",
        team_name="Alpha",
        attempt_number=1,
        base_time_seconds=120,
        gate_penalties=[0, 5, 50],
    )

    runs = load_slalom_runs(db_path, "R4:men:U24")

    assert len(runs) == 1
    assert runs[0].team_name == "Alpha"
    assert runs[0].attempt_number == 1
    assert runs[0].gate_penalties == [0, 5, 50]


def test_save_slalom_run_replaces_existing_attempt(tmp_path: Path) -> None:
    db_path = tmp_path / "replace.db"
    create_competition_db(db_path)

    save_slalom_run(db_path, "R4:men:U24", "Alpha", 1, 120, [0, 5, 0])
    save_slalom_run(db_path, "R4:men:U24", "Alpha", 1, 118, [0, 0, 0])

    runs = load_slalom_runs(db_path, "R4:men:U24")

    assert len(runs) == 1
    assert runs[0].base_time_seconds == 118
    assert runs[0].gate_penalties == [0, 0, 0]


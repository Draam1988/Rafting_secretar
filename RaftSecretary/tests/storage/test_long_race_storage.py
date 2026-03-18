from pathlib import Path

from raftsecretary.domain.status_rules import STATUS_DID_NOT_FINISH, STATUS_OK
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.long_race_storage import load_long_race_entries, save_long_race_entries


def test_save_and_load_long_race_entries(tmp_path: Path) -> None:
    db_path = tmp_path / "long_race.db"
    create_competition_db(db_path)

    entries = [
        SprintEntry(
            team_name="Alpha",
            start_order=1,
            base_time_seconds=3600,
            buoy_penalty_seconds=0,
            behavior_penalty_seconds=0,
            status=STATUS_OK,
        ),
        SprintEntry(
            team_name="Beta",
            start_order=2,
            base_time_seconds=3700,
            buoy_penalty_seconds=50,
            behavior_penalty_seconds=0,
            status=STATUS_DID_NOT_FINISH,
        ),
    ]

    save_long_race_entries(db_path, "R4:men:U24", entries)
    loaded = load_long_race_entries(db_path, "R4:men:U24")

    assert loaded == entries


def test_save_long_race_entries_replaces_previous_entries_for_category(tmp_path: Path) -> None:
    db_path = tmp_path / "replace.db"
    create_competition_db(db_path)

    save_long_race_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry("Old", 1, 100, 0, 0, STATUS_OK)],
    )
    save_long_race_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry("New", 2, 90, 0, 0, STATUS_OK)],
    )

    loaded = load_long_race_entries(db_path, "R4:men:U24")

    assert [entry.team_name for entry in loaded] == ["New"]


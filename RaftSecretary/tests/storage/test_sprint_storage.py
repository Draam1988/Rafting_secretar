from pathlib import Path

from raftsecretary.domain.status_rules import STATUS_DID_NOT_FINISH, STATUS_OK
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.sprint_storage import (
    load_sprint_entries,
    load_sprint_lineup_flags,
    save_sprint_entries,
    save_sprint_lineup_flags,
)


def test_save_and_load_sprint_entries(tmp_path: Path) -> None:
    db_path = tmp_path / "sprint.db"
    create_competition_db(db_path)

    entries = [
        SprintEntry(
            team_name="Storm",
            start_order=1,
            base_time_seconds=80,
            buoy_penalty_seconds=0,
            behavior_penalty_seconds=0,
            status=STATUS_OK,
        ),
        SprintEntry(
            team_name="River",
            start_order=2,
            base_time_seconds=82,
            buoy_penalty_seconds=50,
            behavior_penalty_seconds=0,
            status=STATUS_DID_NOT_FINISH,
        ),
    ]

    save_sprint_entries(db_path, category_key="R4:men:U24", entries=entries)
    loaded = load_sprint_entries(db_path, category_key="R4:men:U24")

    assert loaded == entries


def test_saving_sprint_entries_replaces_previous_entries_for_same_category(tmp_path: Path) -> None:
    db_path = tmp_path / "replace.db"
    create_competition_db(db_path)

    save_sprint_entries(
        db_path,
        category_key="R4:men:U24",
        entries=[
            SprintEntry(
                team_name="Old",
                start_order=1,
                base_time_seconds=80,
                buoy_penalty_seconds=0,
                behavior_penalty_seconds=0,
                status=STATUS_OK,
            )
        ],
    )
    save_sprint_entries(
        db_path,
        category_key="R4:men:U24",
        entries=[
            SprintEntry(
                team_name="New",
                start_order=2,
                base_time_seconds=70,
                buoy_penalty_seconds=0,
                behavior_penalty_seconds=0,
                status=STATUS_OK,
            )
        ],
    )

    loaded = load_sprint_entries(db_path, category_key="R4:men:U24")

    assert [entry.team_name for entry in loaded] == ["New"]


def test_save_and_load_sprint_lineup_flags(tmp_path: Path) -> None:
    db_path = tmp_path / "lineup.db"
    create_competition_db(db_path)

    save_sprint_lineup_flags(
        db_path,
        category_key="R4:men:U16",
        lineup_flags={
            "Storm": {1: True, 2: True, 3: True, 4: False, 5: True},
            "Wave": {1: True, 2: False},
        },
    )

    loaded = load_sprint_lineup_flags(db_path, category_key="R4:men:U16")

    assert loaded == {
        "Storm": {1: True, 2: True, 3: True, 4: False, 5: True},
        "Wave": {1: True, 2: False},
    }

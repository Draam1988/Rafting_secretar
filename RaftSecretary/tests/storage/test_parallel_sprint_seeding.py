from pathlib import Path
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.parallel_sprint_storage import (
    get_seeding, save_seeding, clear_seeding,
    get_manual_mode, set_manual_mode,
)


def test_seeding_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    save_seeding(db, "R4:men:U24", ["T1", "T2", "T3"])
    assert get_seeding(db, "R4:men:U24") == ["T1", "T2", "T3"]


def test_seeding_empty_slots(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    save_seeding(db, "R4:men:U24", ["T1", "", "T3"])
    assert get_seeding(db, "R4:men:U24") == ["T1", "", "T3"]


def test_seeding_overwrite(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    save_seeding(db, "R4:men:U24", ["T1", "T2"])
    save_seeding(db, "R4:men:U24", ["T3", "T4", "T5"])
    assert get_seeding(db, "R4:men:U24") == ["T3", "T4", "T5"]


def test_clear_seeding(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    save_seeding(db, "R4:men:U24", ["T1", "T2"])
    clear_seeding(db, "R4:men:U24")
    assert get_seeding(db, "R4:men:U24") == []


def test_manual_mode_default_is_false(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    assert get_manual_mode(db, "R4:men:U24") is False


def test_manual_mode_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    set_manual_mode(db, "R4:men:U24", True)
    assert get_manual_mode(db, "R4:men:U24") is True
    set_manual_mode(db, "R4:men:U24", False)
    assert get_manual_mode(db, "R4:men:U24") is False


def test_seeding_isolated_by_category(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    create_competition_db(db)
    save_seeding(db, "R4:men:U24", ["T1", "T2"])
    save_seeding(db, "R6:women:U24", ["X1", "X2"])
    assert get_seeding(db, "R4:men:U24") == ["T1", "T2"]
    assert get_seeding(db, "R6:women:U24") == ["X1", "X2"]


def test_clear_protocol_also_clears_seeding(tmp_path: Path) -> None:
    from raftsecretary.storage.parallel_sprint_storage import clear_parallel_sprint_protocol
    db = tmp_path / "e.db"
    create_competition_db(db)
    save_seeding(db, "R4:men:U24", ["T1", "T2", "T3"])
    set_manual_mode(db, "R4:men:U24", True)
    clear_parallel_sprint_protocol(db, "R4:men:U24")
    assert get_seeding(db, "R4:men:U24") == []
    assert get_manual_mode(db, "R4:men:U24") is False

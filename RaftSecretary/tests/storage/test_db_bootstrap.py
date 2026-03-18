from pathlib import Path

from raftsecretary.storage.db import create_competition_db, list_competition_dbs


def test_create_competition_db_creates_sqlite_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test_event.db"

    create_competition_db(db_path)

    assert db_path.exists()
    assert db_path.stat().st_size > 0


def test_list_competition_dbs_returns_only_db_files(tmp_path: Path) -> None:
    create_competition_db(tmp_path / "a_event.db")
    create_competition_db(tmp_path / "b_event.db")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

    result = list_competition_dbs(tmp_path)

    assert [path.name for path in result] == ["a_event.db", "b_event.db"]


from pathlib import Path

from raftsecretary.storage.competition_storage import CompetitionSettingsRecord, save_competition_settings
from raftsecretary.storage.db import create_competition_db
from raftsecretary.web.app import create_app


def test_judges_page_is_reachable_from_dashboard(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/judges?db=event.db")

    assert status == "200 OK"
    assert "Судейский состав" in body
    assert "Главный судья соревнований" in body


def test_export_page_is_reachable_from_dashboard(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/export?db=event.db")

    assert status == "200 OK"
    assert "Протоколы" in body

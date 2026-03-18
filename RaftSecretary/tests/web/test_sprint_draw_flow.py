from pathlib import Path

from raftsecretary.domain.models import Category, Team
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.sprint_storage import load_sprint_entries
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.web.app import create_app


def test_sprint_draw_assigns_unique_start_orders_for_category(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint"],
            categories=[Category("R4", "men", "U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("Alpha", "Moscow", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("Beta", "Tver", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("Gamma", "Perm", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
        ],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/sprint/draw",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "draw_start_time": "10:00",
            "draw_interval": "00:02",
        },
    )

    entries = load_sprint_entries(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/sprint?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert sorted(entry.start_order for entry in entries) == [1, 2, 3]
    assert [entry.start_time for entry in sorted(entries, key=lambda item: item.start_order)] == ["10:00", "10:02", "10:04"]

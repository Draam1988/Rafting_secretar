from pathlib import Path

from raftsecretary.domain.models import Category
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    load_competition_settings,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db


def test_save_and_load_competition_settings(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)

    settings = CompetitionSettingsRecord(
        name="Moscow Championship",
        competition_date="2026-04-01",
        description="River event",
        organizer="Minsport",
        venue="Moscow River",
        enabled_disciplines=["sprint", "slalom"],
        categories=[
            Category(boat_class="R4", sex="men", age_group="U24"),
            Category(boat_class="R6", sex="women", age_group="U20"),
        ],
        slalom_gate_count=10,
        competition_dates=["2026-04-01"],
    )

    save_competition_settings(db_path, settings)
    loaded = load_competition_settings(db_path)

    assert loaded == settings


def test_load_returns_empty_record_for_new_competition(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    create_competition_db(db_path)

    loaded = load_competition_settings(db_path)

    assert loaded.name == ""
    assert loaded.competition_date == ""
    assert loaded.description == ""
    assert loaded.organizer == ""
    assert loaded.venue == ""
    assert loaded.enabled_disciplines == []
    assert loaded.categories == []
    assert loaded.slalom_gate_count == 8


def test_save_and_load_competition_dates_list(tmp_path: Path) -> None:
    db_path = tmp_path / "dates.db"
    create_competition_db(db_path)

    settings = CompetitionSettingsRecord(
        name="Multi Day",
        competition_date="2026-04-01, 2026-04-02",
        competition_dates=["2026-04-01", "2026-04-02"],
        description="Two days",
        organizer="Org",
        venue="Venue",
        enabled_disciplines=["sprint"],
        categories=[],
        slalom_gate_count=8,
    )

    save_competition_settings(db_path, settings)
    loaded = load_competition_settings(db_path)

    assert loaded.competition_dates == ["2026-04-01", "2026-04-02"]

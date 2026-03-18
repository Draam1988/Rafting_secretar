from pathlib import Path

from raftsecretary.domain.models import Category
from raftsecretary.storage.competition_storage import CompetitionSettingsRecord, save_competition_settings
from raftsecretary.storage.db import create_competition_db
from raftsecretary.web.app import create_app


def test_teams_page_contains_age_validation_metadata_for_u16(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/teams?db=event.db")

    assert status == "200 OK"
    assert 'data-age-min="2011"' in body
    assert 'data-age-max="2014"' in body
    assert "year-warning" in body
    assert "$<built-in function min>" not in body


def test_teams_page_contains_age_validation_metadata_for_u20_and_u24(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=[],
            categories=[Category("R4", "men", "U20"), Category("R6", "women", "U24")],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/teams?db=event.db")

    assert status == "200 OK"
    assert 'data-age-min="2007"' in body
    assert 'data-age-max="2012"' in body
    assert 'data-age-min="2003"' in body
    assert 'data-age-max="2012"' in body


def test_age_validation_uses_first_competition_day_year(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="27-29.03.2025",
            competition_dates=["2025-03-27", "2025-03-28", "2025-03-29"],
            description="",
            enabled_disciplines=[],
            categories=[Category("R4", "men", "U16")],
            slalom_gate_count=8,
        ),
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/teams?db=event.db")

    assert status == "200 OK"
    assert 'data-age-min="2010"' in body
    assert 'data-age-max="2013"' in body

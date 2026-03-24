import sqlite3
from pathlib import Path

from raftsecretary.domain.models import Category
from raftsecretary.storage.competition_storage import load_competition_settings
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.team_storage import load_teams
from raftsecretary.web.app import create_app


def test_update_settings_endpoint_saves_competition_settings(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/settings/save",
        form_data={
            "db": "event.db",
            "name": "Spring Cup",
            "competition_date_1": "2026-05-10",
            "competition_date_2": "2026-05-11",
            "description": "Test river",
            "organizer_1": "Минспорт",
            "venue": "р. Белая",
            "discipline_sprint": "on",
            "discipline_parallel_sprint": "on",
            "discipline_slalom": "on",
            "slalom_gate_count": "12",
            "category__R4__men__U24": "on",
        },
    )

    saved = load_competition_settings(db_path)

    assert status == "303 See Other"
    assert ("Location", "/settings?db=event.db") in headers
    assert body == ""
    assert saved.name == "Spring Cup"
    assert saved.competition_dates == ["2026-05-10", "2026-05-11"]
    assert "Минспорт" in saved.organizers
    assert saved.venue == "р. Белая"
    assert saved.enabled_disciplines == ["sprint", "parallel_sprint", "slalom"]
    assert saved.slalom_gate_count == 12
    assert saved.categories == [Category(boat_class="R4", sex="men", age_group="U24")]


def test_add_team_endpoint_saves_team_and_athletes(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Storm",
            "region": "Moscow",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "1",
            "athletes": "A1,A2,A3,A4",
        },
    )

    teams = load_teams(db_path)

    assert status == "303 See Other"
    assert ("Location", "/teams?db=event.db&open_category=R4%3Amen%3AU24#category-R4-men-U24") in headers
    assert body == ""
    assert len(teams) == 1
    assert teams[0].name == "Storm"
    assert teams[0].athletes == ["A1", "A2", "A3", "A4"]


def test_edit_team_endpoint_replaces_existing_team_data(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Storm",
            "region": "Moscow",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "1",
            "athletes": "A1,A2,A3,A4",
        },
    )

    status, headers, body = app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "editing_category_key": "R4:men:U24",
            "editing_start_number": "1",
            "name": "Storm Updated",
            "region": "Tver",
            "club": "New Club",
            "representative_full_name": "Иванов Иван Иванович",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "1",
            "athletes": "B1,B2,B3,B4",
        },
    )

    teams = load_teams(db_path)

    assert status == "303 See Other"
    assert ("Location", "/teams?db=event.db&open_category=R4%3Amen%3AU24#category-R4-men-U24") in headers
    assert body == ""
    assert len(teams) == 1
    assert teams[0].name == "Storm Updated"
    assert teams[0].region == "Tver"
    assert teams[0].club == "New Club"


def test_edit_team_page_keeps_target_category_open(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/settings/save",
        form_data={
            "db": "event.db",
            "name": "Cup",
            "competition_date": "2026-03-15",
            "description": "",
            "category__R4__men__U24": "on",
            "category__R6__women__U20": "on",
        },
    )
    app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Storm",
            "region": "Moscow",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "1",
            "athletes": "A1,A2,A3,A4",
        },
    )

    status, _, body = app.handle("GET", "/teams?db=event.db&edit_category=R4%3Amen%3AU24&edit_number=1")

    assert status == "200 OK"
    assert 'class="tc-category"' in body
    assert 'open>' in body
    assert 'value="Storm"' in body


def test_edit_team_page_targets_exact_team_even_with_duplicate_numbers(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/settings/save",
        form_data={
            "db": "event.db",
            "name": "Cup",
            "competition_date": "2026-03-15",
            "description": "",
            "category__R4__men__U24": "on",
        },
    )
    app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Storm",
            "region": "Moscow",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "7",
            "athletes": "A1,A2,A3,A4",
        },
    )
    app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Wave",
            "region": "Perm",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "8",
            "athletes": "B1,B2,B3,B4",
        },
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE teams SET start_number = 7 WHERE name = 'Wave'")
        wave_id = connection.execute("SELECT id FROM teams WHERE name = 'Wave'").fetchone()[0]
        connection.commit()

    status, _, body = app.handle("GET", f"/teams?db=event.db&edit_category=R4%3Amen%3AU24&edit_team_id={wave_id}")

    assert status == "200 OK"
    assert 'value="Wave"' in body
    assert 'value="Perm"' in body


def test_add_team_redirect_keeps_category_open(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, _ = app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Storm",
            "region": "Moscow",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "1",
            "athletes": "A1,A2,A3,A4",
        },
    )

    assert status == "303 See Other"
    assert ("Location", "/teams?db=event.db&open_category=R4%3Amen%3AU24#category-R4-men-U24") in headers


def test_add_team_endpoint_saves_structured_members_with_year_and_custom_rank(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/teams/add",
        form_data={
            "db": "event.db",
            "name": "Wave",
            "region": "Krasnodar",
            "club": "Wave Club",
            "representative_full_name": "Иванов Иван Иванович",
            "boat_class": "R4",
            "sex": "men",
            "age_group": "U24",
            "start_number": "7",
            "member_1_full_name": "Петров Петр Петрович",
            "member_1_birth_date": "2008",
            "member_1_rank": "1 разряд",
            "member_1_role": "main",
            "member_2_full_name": "Сидоров Сидор Сидорович",
            "member_2_birth_date": "2009",
            "member_2_rank_custom": "Без разряда",
            "member_2_role": "main",
        },
    )

    teams = load_teams(db_path)

    assert status == "303 See Other"
    assert ("Location", "/teams?db=event.db&open_category=R4%3Amen%3AU24#category-R4-men-U24") in headers
    assert body == ""
    assert len(teams) == 1
    assert len(teams[0].members) == 2
    assert teams[0].members[0].birth_date == "2008"
    assert teams[0].members[0].rank == "1 разряд"
    assert teams[0].members[1].rank == "Б/Р"

from pathlib import Path

from raftsecretary.domain.models import Category, Team
from raftsecretary.storage.competition_storage import (
    CompetitionSettingsRecord,
    save_competition_settings,
)
from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.parallel_sprint_storage import (
    get_manual_mode,
    get_seeding,
    load_parallel_sprint_heats,
    load_parallel_sprint_start_entries,
    set_manual_mode,
)
from raftsecretary.storage.sprint_storage import save_sprint_entries
from raftsecretary.storage.team_storage import save_teams
from raftsecretary.domain.sprint import SprintEntry
from raftsecretary.domain.status_rules import STATUS_OK
from raftsecretary.web.app import create_app


def test_parallel_sprint_page_shows_start_table_for_all_crews(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
            Team("T4", "D", "R4", "men", "U24", 4, ["D1", "D2", "D3", "D4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("T1", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("T2", 2, 81, 0, 0, STATUS_OK),
            SprintEntry("T3", 3, 82, 0, 0, STATUS_OK),
            SprintEntry("T4", 4, 83, 0, 0, STATUS_OK),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "H2H" in body
    assert "Стартовый протокол" in body
    assert "Сформировать старт" in body
    assert "T1" in body and "T4" in body
    assert "T2" in body and "T3" in body
    assert "Время старта" in body
    assert "№ команды" in body
    assert "Команда" in body
    assert "Состав" in body


def test_parallel_sprint_page_shows_all_crews_for_five_teams_and_rules_hint(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
            Team("T4", "D", "R4", "men", "U24", 4, ["D1", "D2", "D3", "D4"]),
            Team("T5", "E", "R4", "men", "U24", 5, ["E1", "E2", "E3", "E4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("T1", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("T2", 2, 81, 0, 0, STATUS_OK),
            SprintEntry("T3", 3, 82, 0, 0, STATUS_OK),
            SprintEntry("T4", 4, 83, 0, 0, STATUS_OK),
            SprintEntry("T5", 5, 84, 0, 0, STATUS_OK),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "T1" in body and "T5" in body
    assert "Все участники категории" in body
    assert "Сетка H2H формируется по результатам спринта" in body


def test_parallel_sprint_build_assigns_start_times_to_all_crews(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("T1", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("T2", 2, 81, 0, 0, STATUS_OK),
            SprintEntry("T3", 3, 82, 0, 0, STATUS_OK),
        ],
    )
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/parallel-sprint/build",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "draw_start_time": "10:00",
            "draw_interval": "00:02",
        },
    )

    start_entries = load_parallel_sprint_start_entries(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/parallel-sprint?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert [entry.team_name for entry in start_entries] == ["T1", "T2", "T3"]
    assert [entry.start_order for entry in start_entries] == [1, 2, 3]
    assert [entry.start_time for entry in start_entries] == ["10:00", "10:02", "10:04"]


def test_parallel_sprint_page_shows_clear_actions_and_time_masks(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
            Team("T4", "D", "R4", "men", "U24", 4, ["D1", "D2", "D3", "D4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("T1", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("T2", 2, 81, 0, 0, STATUS_OK),
            SprintEntry("T3", 3, 82, 0, 0, STATUS_OK),
            SprintEntry("T4", 4, 83, 0, 0, STATUS_OK),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "Очистить протокол" in body
    assert 'data-time-mask="hhmm"' in body


def test_parallel_sprint_save_endpoint_persists_heat_result(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/parallel-sprint/save",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "round_name": "semifinal_1",
            "left_team_name": "T1",
            "left_start_order": "1",
            "left_total_time_seconds": "120",
            "left_missed_buoys": "0",
            "left_status": "OK",
            "right_team_name": "T4",
            "right_start_order": "4",
            "right_total_time_seconds": "125",
            "right_missed_buoys": "0",
            "right_status": "OK",
        },
    )

    heats = load_parallel_sprint_heats(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert ("Location", "/parallel-sprint?db=event.db&category=R4%3Amen%3AU24") in headers
    assert body == ""
    assert len(heats) == 1
    assert heats[0][0] == "semifinal_1"


def test_parallel_sprint_result_panel_saves_single_side_result(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
            Team("T4", "D", "R4", "men", "U24", 4, ["D1", "D2", "D3", "D4"]),
            Team("T5", "E", "R4", "men", "U24", 5, ["E1", "E2", "E3", "E4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("T1", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("T2", 2, 81, 0, 0, STATUS_OK),
            SprintEntry("T3", 3, 82, 0, 0, STATUS_OK),
            SprintEntry("T4", 4, 83, 0, 0, STATUS_OK),
            SprintEntry("T5", 5, 84, 0, 0, STATUS_OK),
        ],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24&open_result=stage1_seed_4%7Cleft")

    assert status == "200 OK"
    assert "Результат заезда" in body
    assert "1й буй" in body
    assert "2й буй" in body

    status, headers, body = app.handle(
        "POST",
        "/parallel-sprint/result",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "round_name": "stage1_seed_4",
            "lane": "left",
            "team_name": "T4",
            "team_start_order": "4",
            "other_team_name": "T5",
            "other_start_order": "5",
            "base_time_seconds": "00:48",
            "buoy_one": "50",
            "buoy_two": "0",
        },
    )

    heats = load_parallel_sprint_heats(db_path, "R4:men:U24")

    assert status == "303 See Other"
    assert (
        "Location",
        "/parallel-sprint?db=event.db&category=R4%3Amen%3AU24&open_result=stage1_seed_4%7Cleft#h2h-stage-1",
    ) in headers
    assert body == ""
    assert len(heats) == 1
    assert heats[0][0] == "stage1_seed_4"
    assert heats[0][1].team_name == "T4"
    assert heats[0][1].total_time_seconds == 98

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "16666:39" not in body


def test_parallel_sprint_shows_second_stage_after_all_first_stage_results(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    teams = [
        Team(f"T{i}", f"R{i}", "R4", "men", "U24", i, [f"A{i}1", f"A{i}2", f"A{i}3", f"A{i}4"])
        for i in range(1, 12)
    ]
    save_teams(db_path, teams)
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry(f"T{i}", i, 70 + i, 0, 0, STATUS_OK) for i in range(1, 12)],
    )
    app = create_app(tmp_path)

    for round_name, lane, team_name, start_order, other_team_name, other_start_order, base_time in [
        ("stage1_seed_6", "left", "T6", "6", "T11", "11", "00:41"),
        ("stage1_seed_6", "right", "T11", "11", "T6", "6", "00:46"),
        ("stage1_seed_7", "left", "T7", "7", "T10", "10", "00:42"),
        ("stage1_seed_7", "right", "T10", "10", "T7", "7", "00:47"),
        ("stage1_seed_8", "left", "T8", "8", "T9", "9", "00:43"),
        ("stage1_seed_8", "right", "T9", "9", "T8", "8", "00:48"),
    ]:
        app.handle(
            "POST",
            "/parallel-sprint/result",
            form_data={
                "db": "event.db",
                "category_key": "R4:men:U24",
                "round_name": round_name,
                "lane": lane,
                "team_name": team_name,
                "team_start_order": start_order,
                "other_team_name": other_team_name,
                "other_start_order": other_start_order,
                "base_time_seconds": base_time,
                "buoy_one": "0",
                "buoy_two": "0",
            },
        )

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "1/4 финала" in body
    assert "quarterfinal_1" in body
    assert "quarterfinal_4" in body


def test_parallel_sprint_shows_semifinal_stage_after_winners_second_stage_result(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    teams = [
        Team(f"T{i}", f"R{i}", "R4", "men", "U24", i, [f"A{i}1", f"A{i}2", f"A{i}3", f"A{i}4"])
        for i in range(1, 12)
    ]
    save_teams(db_path, teams)
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry(f"T{i}", i, 70 + i, 0, 0, STATUS_OK) for i in range(1, 12)],
    )
    app = create_app(tmp_path)

    for round_name, left_name, left_seed, left_time, right_name, right_seed, right_time in [
        ("stage1_seed_6", "T6", "6", "00:41", "T11", "11", "00:46"),
        ("stage1_seed_7", "T7", "7", "00:42", "T10", "10", "00:47"),
        ("stage1_seed_8", "T8", "8", "00:43", "T9", "9", "00:48"),
        ("quarterfinal_1", "T1", "1", "00:40", "T8", "8", "00:49"),
        ("quarterfinal_2", "T4", "4", "00:41", "T5", "5", "00:50"),
        ("quarterfinal_3", "T2", "2", "00:42", "T7", "7", "00:51"),
        ("quarterfinal_4", "T3", "3", "00:43", "T6", "6", "00:52"),
    ]:
        app.handle(
            "POST",
            "/parallel-sprint/result",
            form_data={
                "db": "event.db",
                "category_key": "R4:men:U24",
                "round_name": round_name,
                "lane": "left",
                "team_name": left_name,
                "team_start_order": left_seed,
                "other_team_name": right_name,
                "other_start_order": right_seed,
                "base_time_seconds": left_time,
                "buoy_one": "0",
                "buoy_two": "0",
            },
        )
        app.handle(
            "POST",
            "/parallel-sprint/result",
            form_data={
                "db": "event.db",
                "category_key": "R4:men:U24",
                "round_name": round_name,
                "lane": "right",
                "team_name": right_name,
                "team_start_order": right_seed,
                "other_team_name": left_name,
                "other_start_order": left_seed,
                "base_time_seconds": right_time,
                "buoy_one": "0",
                "buoy_two": "0",
            },
        )

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "1/2 финала" in body
    assert "semifinal_1" in body
    assert "semifinal_2" in body


def test_parallel_sprint_shows_finals_and_standings_after_semis_complete(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    teams = [
        Team(f"T{i}", f"R{i}", "R4", "men", "U24", i, [f"A{i}1", f"A{i}2", f"A{i}3", f"A{i}4"])
        for i in range(1, 12)
    ]
    save_teams(db_path, teams)
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry(f"T{i}", i, 70 + i, 0, 0, STATUS_OK) for i in range(1, 12)],
    )
    app = create_app(tmp_path)

    payloads = [
        ("stage1_seed_6", "left", "T6", "6", "T11", "11", "00:41"),
        ("stage1_seed_6", "right", "T11", "11", "T6", "6", "00:46"),
        ("stage1_seed_7", "left", "T7", "7", "T10", "10", "00:42"),
        ("stage1_seed_7", "right", "T10", "10", "T7", "7", "00:47"),
        ("stage1_seed_8", "left", "T8", "8", "T9", "9", "00:43"),
        ("stage1_seed_8", "right", "T9", "9", "T8", "8", "00:48"),
        ("quarterfinal_1", "left", "T1", "1", "T8", "8", "00:40"),
        ("quarterfinal_1", "right", "T8", "8", "T1", "1", "00:50"),
        ("quarterfinal_2", "left", "T4", "4", "T5", "5", "00:41"),
        ("quarterfinal_2", "right", "T5", "5", "T4", "4", "00:52"),
        ("quarterfinal_3", "left", "T2", "2", "T7", "7", "00:43"),
        ("quarterfinal_3", "right", "T7", "7", "T2", "2", "00:54"),
        ("quarterfinal_4", "left", "T3", "3", "T6", "6", "00:44"),
        ("quarterfinal_4", "right", "T6", "6", "T3", "3", "00:55"),
        ("semifinal_1", "left", "T1", "1", "T4", "4", "00:40"),
        ("semifinal_1", "right", "T4", "4", "T1", "1", "00:49"),
        ("semifinal_2", "left", "T2", "2", "T3", "3", "00:41"),
        ("semifinal_2", "right", "T3", "3", "T2", "2", "00:50"),
    ]
    for round_name, lane, team_name, start_order, other_team_name, other_start_order, base_time in payloads:
        app.handle(
            "POST",
            "/parallel-sprint/result",
            form_data={
                "db": "event.db",
                "category_key": "R4:men:U24",
                "round_name": round_name,
                "lane": lane,
                "team_name": team_name,
                "team_start_order": start_order,
                "other_team_name": other_team_name,
                "other_start_order": other_start_order,
                "base_time_seconds": base_time,
                "buoy_one": "0",
                "buoy_two": "0",
            },
        )

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")
    assert status == "200 OK"
    assert "Финал A" in body
    assert "final_a" in body
    assert "Финал B" in body
    assert "final_b" in body

    for round_name, lane, team_name, start_order, other_team_name, other_start_order, base_time in [
        ("final_a", "left", "T1", "1", "T2", "2", "00:40"),
        ("final_a", "right", "T2", "2", "T1", "1", "00:47"),
        ("final_b", "left", "T4", "4", "T3", "3", "00:41"),
        ("final_b", "right", "T3", "3", "T4", "4", "00:48"),
    ]:
        app.handle(
            "POST",
            "/parallel-sprint/result",
            form_data={
                "db": "event.db",
                "category_key": "R4:men:U24",
                "round_name": round_name,
                "lane": lane,
                "team_name": team_name,
                "team_start_order": start_order,
                "other_team_name": other_team_name,
                "other_start_order": other_start_order,
                "base_time_seconds": base_time,
                "buoy_one": "0",
                "buoy_two": "0",
            },
        )

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")

    assert status == "200 OK"
    assert "Итоговые места H2H" in body
    assert ">1<" in body
    assert ">2<" in body
    assert ">3<" in body
    assert ">4<" in body
    assert "T1" in body
    assert "T2" in body
    assert "T4" in body
    assert "T3" in body


def test_parallel_sprint_clear_protocol_resets_start_and_results(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [Team(f"T{i}", f"R{i}", "R4", "men", "U24", i, [f"A{i}1", f"A{i}2", f"A{i}3", f"A{i}4"]) for i in range(1, 6)],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry(f"T{i}", i, 70 + i, 0, 0, STATUS_OK) for i in range(1, 6)],
    )
    app = create_app(tmp_path)

    app.handle(
        "POST",
        "/parallel-sprint/build",
        form_data={"db": "event.db", "category_key": "R4:men:U24", "draw_start_time": "10:00", "draw_interval": "00:02"},
    )
    app.handle(
        "POST",
        "/parallel-sprint/result",
        form_data={
            "db": "event.db",
            "category_key": "R4:men:U24",
            "round_name": "stage1_seed_4",
            "lane": "left",
            "team_name": "T4",
            "team_start_order": "4",
            "other_team_name": "T5",
            "other_start_order": "5",
            "base_time_seconds": "00:48",
            "buoy_one": "50",
            "buoy_two": "0",
        },
    )

    status, headers, _ = app.handle(
        "POST",
        "/parallel-sprint/clear",
        form_data={"db": "event.db", "category_key": "R4:men:U24"},
    )

    assert status == "303 See Other"
    assert ("Location", "/parallel-sprint?db=event.db&category=R4%3Amen%3AU24") in headers
    assert load_parallel_sprint_start_entries(db_path, "R4:men:U24") == []
    assert load_parallel_sprint_heats(db_path, "R4:men:U24") == []


def test_parallel_sprint_clear_stage_removes_selected_stage_and_later(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    teams = [
        Team(f"T{i}", f"R{i}", "R4", "men", "U24", i, [f"A{i}1", f"A{i}2", f"A{i}3", f"A{i}4"])
        for i in range(1, 12)
    ]
    save_teams(db_path, teams)
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry(f"T{i}", i, 70 + i, 0, 0, STATUS_OK) for i in range(1, 12)],
    )
    app = create_app(tmp_path)

    payloads = [
        ("stage1_seed_6", "left", "T6", "6", "T11", "11", "00:41"),
        ("stage1_seed_6", "right", "T11", "11", "T6", "6", "00:46"),
        ("stage1_seed_7", "left", "T7", "7", "T10", "10", "00:42"),
        ("stage1_seed_7", "right", "T10", "10", "T7", "7", "00:47"),
        ("stage1_seed_8", "left", "T8", "8", "T9", "9", "00:43"),
        ("stage1_seed_8", "right", "T9", "9", "T8", "8", "00:48"),
        ("quarterfinal_1", "left", "T1", "1", "T8", "8", "00:40"),
        ("quarterfinal_1", "right", "T8", "8", "T1", "1", "00:50"),
        ("quarterfinal_2", "left", "T4", "4", "T5", "5", "00:41"),
        ("quarterfinal_2", "right", "T5", "5", "T4", "4", "00:52"),
        ("quarterfinal_3", "left", "T2", "2", "T7", "7", "00:43"),
        ("quarterfinal_3", "right", "T7", "7", "T2", "2", "00:54"),
        ("quarterfinal_4", "left", "T3", "3", "T6", "6", "00:44"),
        ("quarterfinal_4", "right", "T6", "6", "T3", "3", "00:55"),
        ("semifinal_1", "left", "T1", "1", "T4", "4", "00:40"),
        ("semifinal_1", "right", "T4", "4", "T1", "1", "00:49"),
    ]
    for round_name, lane, team_name, start_order, other_team_name, other_start_order, base_time in payloads:
        app.handle(
            "POST",
            "/parallel-sprint/result",
            form_data={
                "db": "event.db",
                "category_key": "R4:men:U24",
                "round_name": round_name,
                "lane": lane,
                "team_name": team_name,
                "team_start_order": start_order,
                "other_team_name": other_team_name,
                "other_start_order": other_start_order,
                "base_time_seconds": base_time,
                "buoy_one": "0",
                "buoy_two": "0",
            },
        )

    status, headers, _ = app.handle(
        "POST",
        "/parallel-sprint/clear-stage",
        form_data={"db": "event.db", "category_key": "R4:men:U24", "stage_title": "1/4 финала"},
    )

    heats = {round_name for round_name, _left, _right in load_parallel_sprint_heats(db_path, "R4:men:U24")}

    assert status == "303 See Other"
    assert ("Location", "/parallel-sprint?db=event.db&category=R4%3Amen%3AU24") in headers
    assert "stage1_seed_6" in heats
    assert "quarterfinal_1" not in heats
    assert "semifinal_1" not in heats

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24")
    assert status == "200 OK"
    assert "1/4 финала" in body
    assert "1/2 финала" not in body


def test_parallel_sprint_result_panel_uses_only_current_category_teams_after_deletions(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
            Team("T4", "D", "R4", "men", "U24", 4, ["D1", "D2", "D3", "D4"]),
            Team("T5", "E", "R4", "men", "U24", 5, ["E1", "E2", "E3", "E4"]),
            Team("T6", "F", "R4", "men", "U24", 6, ["F1", "F2", "F3", "F4"]),
            Team("T7", "G", "R4", "men", "U24", 7, ["G1", "G2", "G3", "G4"]),
            Team("T8", "H", "R4", "men", "U24", 8, ["H1", "H2", "H3", "H4"]),
            Team("T9", "I", "R4", "men", "U24", 9, ["I1", "I2", "I3", "I4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [SprintEntry(f"T{i}", i, 70 + i, 0, 0, STATUS_OK) for i in range(1, 12)],
    )
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/parallel-sprint?db=event.db&category=R4:men:U24&open_result=stage1_seed_8%7Cleft")

    assert status == "200 OK"
    assert "T8 · Первый этап" in body
    assert "T9" in body
    assert "T10" not in body


def _make_app_with_4_teams(tmp_path: Path):
    """Helper: competition with 4 teams + sprint results."""
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    save_competition_settings(
        db_path,
        CompetitionSettingsRecord(
            name="Cup",
            competition_date="2026-03-15",
            description="",
            enabled_disciplines=["sprint", "parallel_sprint"],
            categories=[Category(boat_class="R4", sex="men", age_group="U24")],
            slalom_gate_count=8,
        ),
    )
    save_teams(
        db_path,
        [
            Team("T1", "A", "R4", "men", "U24", 1, ["A1", "A2", "A3", "A4"]),
            Team("T2", "B", "R4", "men", "U24", 2, ["B1", "B2", "B3", "B4"]),
            Team("T3", "C", "R4", "men", "U24", 3, ["C1", "C2", "C3", "C4"]),
            Team("T4", "D", "R4", "men", "U24", 4, ["D1", "D2", "D3", "D4"]),
        ],
    )
    save_sprint_entries(
        db_path,
        "R4:men:U24",
        [
            SprintEntry("T1", 1, 80, 0, 0, STATUS_OK),
            SprintEntry("T2", 2, 81, 0, 0, STATUS_OK),
            SprintEntry("T3", 3, 82, 0, 0, STATUS_OK),
            SprintEntry("T4", 4, 83, 0, 0, STATUS_OK),
        ],
    )
    return create_app(tmp_path), "event.db"


def test_set_mode_saves_manual_flag(tmp_path: Path) -> None:
    app, db_name = _make_app_with_4_teams(tmp_path)
    status, _, _ = app.handle(
        "POST",
        "/parallel-sprint/set-mode",
        form_data={"db": db_name, "category_key": "R4:men:U24", "manual": "1"},
    )
    assert status == "303 See Other"
    assert get_manual_mode(tmp_path / db_name, "R4:men:U24") is True


def test_assign_slot_saves_seeding(tmp_path: Path) -> None:
    app, db_name = _make_app_with_4_teams(tmp_path)
    db_path = tmp_path / db_name
    from raftsecretary.storage.parallel_sprint_storage import save_seeding as _save_seeding
    _save_seeding(db_path, "R4:men:U24", ["", "", "", ""])
    status, _, _ = app.handle(
        "POST",
        "/parallel-sprint/assign-slot",
        form_data={"db": db_name, "category_key": "R4:men:U24", "slot_index": "2", "team_name": "T3"},
    )
    assert status == "303 See Other"
    seeding = get_seeding(db_path, "R4:men:U24")
    assert seeding[1] == "T3"


def test_assign_slot_moves_team_from_old_position(tmp_path: Path) -> None:
    app, db_name = _make_app_with_4_teams(tmp_path)
    db_path = tmp_path / db_name
    from raftsecretary.storage.parallel_sprint_storage import save_seeding as _save_seeding
    _save_seeding(db_path, "R4:men:U24", ["T1", "T2", "T3", "T4"])
    app.handle(
        "POST",
        "/parallel-sprint/assign-slot",
        form_data={"db": db_name, "category_key": "R4:men:U24", "slot_index": "1", "team_name": "T3"},
    )
    seeding = get_seeding(db_path, "R4:men:U24")
    assert seeding[0] == "T3"
    assert seeding[2] == ""


def test_clear_slot_empties_position(tmp_path: Path) -> None:
    app, db_name = _make_app_with_4_teams(tmp_path)
    db_path = tmp_path / db_name
    from raftsecretary.storage.parallel_sprint_storage import save_seeding as _save_seeding
    _save_seeding(db_path, "R4:men:U24", ["T1", "T2", "T3", "T4"])
    app.handle(
        "POST",
        "/parallel-sprint/clear-slot",
        form_data={"db": db_name, "category_key": "R4:men:U24", "slot_index": "2"},
    )
    seeding = get_seeding(db_path, "R4:men:U24")
    assert seeding[1] == ""
    assert seeding[0] == "T1"


def test_auto_build_saves_seeding(tmp_path: Path) -> None:
    app, db_name = _make_app_with_4_teams(tmp_path)
    app.handle(
        "POST",
        "/parallel-sprint/build",
        form_data={"db": db_name, "category_key": "R4:men:U24",
                   "draw_start_time": "10:00", "draw_interval": "00:02"},
    )
    seeding = get_seeding(tmp_path / db_name, "R4:men:U24")
    assert len(seeding) == 4
    assert seeding[0] == "T1"  # sprint rank 1 first


def test_manual_build_creates_empty_slots(tmp_path: Path) -> None:
    app, db_name = _make_app_with_4_teams(tmp_path)
    db_path = tmp_path / db_name
    set_manual_mode(db_path, "R4:men:U24", True)
    app.handle(
        "POST",
        "/parallel-sprint/build",
        form_data={"db": db_name, "category_key": "R4:men:U24",
                   "draw_start_time": "10:00", "draw_interval": "00:02"},
    )
    seeding = get_seeding(db_path, "R4:men:U24")
    assert len(seeding) == 4
    assert all(name == "" for name in seeding)

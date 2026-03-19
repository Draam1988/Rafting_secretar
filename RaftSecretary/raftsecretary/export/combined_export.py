from __future__ import annotations
from pathlib import Path

from raftsecretary.domain.sprint import SprintEntry, rank_sprint_entries
from raftsecretary.domain.combined import combine_points
from raftsecretary.domain.points import points_for_place
from raftsecretary.storage.competition_storage import load_competition_settings
from raftsecretary.storage.judges_storage import load_judges
from raftsecretary.storage.sprint_storage import load_sprint_entries
from raftsecretary.storage.slalom_storage import load_slalom_runs
from raftsecretary.storage.parallel_sprint_storage import load_parallel_sprint_heats
from raftsecretary.storage.long_race_storage import load_long_race_entries
from raftsecretary.storage.team_storage import load_teams
from raftsecretary.export.pdf_builder import (
    new_pdf, pdf_bytes, write_doc_header, write_category_header,
    write_table_header, write_table_row, write_footer,
)
from raftsecretary.export.xlsx_builder import (
    new_workbook, workbook_bytes, write_meta_row, write_header_row, write_data_row,
)
from raftsecretary.export.sprint_export import _judge_name, _category_label, _normalize_status
from raftsecretary.web.app import (
    _place_map_from_ranked_entries, _points_from_ranked_entries,
    _long_race_points_from_ranked_entries, _slalom_places_map, _slalom_points_map,
    _parallel_sprint_full_places_map,
)

COMBINED_COLS_PDF = [
    ("№", 8), ("Команда", 38), ("Состав", 42), ("Субъект", 28),
    ("Спринт м/о", 20), ("H2H м/о", 20), ("Слалом м/о", 20),
    ("Длинная м/о", 20), ("Итого м/о", 20),
]
COMBINED_COLS_XLSX = [
    ("№", 6), ("Команда", 22), ("Состав", 28), ("Субъект", 18),
    ("Спринт место", 10), ("Спринт очки", 10),
    ("H2H место", 8), ("H2H очки", 8),
    ("Слалом место", 10), ("Слалом очки", 10),
    ("Длинная место", 10), ("Длинная очки", 10),
    ("Итого место", 8), ("Итого очки", 8),
]


def _to_entry(e) -> SprintEntry:
    return SprintEntry(
        team_name=e.team_name, start_order=e.start_order,
        base_time_seconds=e.base_time_seconds,
        buoy_penalty_seconds=e.buoy_penalty_seconds,
        behavior_penalty_seconds=e.behavior_penalty_seconds,
        status=_normalize_status(e.status),
        start_time=e.start_time,
    )


def _load_data(db_path: Path):
    settings = load_competition_settings(db_path)
    judges = load_judges(db_path)
    teams = load_teams(db_path)
    comp_dates = ", ".join(settings.competition_dates or [settings.competition_date])
    return settings, judges, teams, comp_dates


def _calc_combined(db_path, category, teams):
    category_teams = [t for t in teams if t.category_key == category.key]
    if not category_teams:
        return None

    sprint_ranked = rank_sprint_entries([_to_entry(e) for e in load_sprint_entries(db_path, category.key)])
    sprint_places = _place_map_from_ranked_entries(sprint_ranked)
    sprint_pts = _points_from_ranked_entries("sprint", sprint_ranked)

    lr_ranked = rank_sprint_entries([_to_entry(e) for e in load_long_race_entries(db_path, category.key)])
    lr_places = _place_map_from_ranked_entries(lr_ranked)
    lr_pts = _long_race_points_from_ranked_entries(lr_ranked)

    slalom_runs = load_slalom_runs(db_path, category.key)
    slalom_places = _slalom_places_map(slalom_runs)
    slalom_pts = _slalom_points_map(slalom_runs)

    heats = load_parallel_sprint_heats(db_path, category.key)
    saved = {rn: (l, r) for rn, l, r in heats}
    h2h_places = _parallel_sprint_full_places_map(category_teams, saved)
    h2h_pts = {tn: points_for_place("parallel_sprint", p) for tn, p in h2h_places.items()}

    combined_rows = combine_points(sprint_points=sprint_pts, parallel_sprint_points=h2h_pts,
                                    slalom_points=slalom_pts, long_race_points=lr_pts)
    comb_places = {tn: i for i, (tn, _) in enumerate(combined_rows, 1)}
    comb_pts = {tn: p for tn, p in combined_rows}

    return category_teams, sprint_places, sprint_pts, h2h_places, h2h_pts, slalom_places, slalom_pts, lr_places, lr_pts, comb_places, comb_pts


def build_combined_pdf(db_path: Path) -> bytes:
    settings, judges, teams, comp_dates = _load_data(db_path)
    pdf = new_pdf()
    pdf.add_page()
    write_doc_header(pdf, "Многоборье", settings.name or "", comp_dates,
                     settings.venue or "", settings.organizer or "")

    for category in settings.categories:
        result = _calc_combined(db_path, category, teams)
        if result is None:
            continue
        category_teams, sp_pl, sp_pts, h2h_pl, h2h_pts, sl_pl, sl_pts, lr_pl, lr_pts, comb_pl, comb_pts = result

        write_category_header(pdf, _category_label(category))
        write_table_header(pdf, COMBINED_COLS_PDF)

        for team in sorted(category_teams, key=lambda t: (comb_pl.get(t.name, 9999), t.start_number)):
            main_m = [m for m in team.crew_members if m.role != "reserve"]
            lineup = "; ".join(m.full_name for m in main_m) or ""

            def cell(pl, pts):
                return f"{pl}/{pts}" if pl else ""

            write_table_row(pdf, [
                (str(team.start_number), 8), (team.name, 38),
                (lineup[:30], 42), (team.region, 28),
                (cell(sp_pl.get(team.name), sp_pts.get(team.name, 0)), 20),
                (cell(h2h_pl.get(team.name), h2h_pts.get(team.name, 0)), 20),
                (cell(sl_pl.get(team.name), sl_pts.get(team.name, 0)), 20),
                (cell(lr_pl.get(team.name), lr_pts.get(team.name, 0)), 20),
                (cell(comb_pl.get(team.name), comb_pts.get(team.name, 0)), 20),
            ])
        pdf.ln(3)

    write_footer(pdf, _judge_name(judges.chief_judge), _judge_name(judges.chief_secretary))
    return pdf_bytes(pdf)


def build_combined_xlsx(db_path: Path) -> bytes:
    from openpyxl.styles import Font as XFont
    settings, judges, teams, comp_dates = _load_data(db_path)
    wb, ws = new_workbook()
    ws.title = "Многоборье"

    row = 1
    write_meta_row(ws, row, "Соревнование", settings.name or ""); row += 1
    write_meta_row(ws, row, "Даты", comp_dates); row += 1
    write_meta_row(ws, row, "Место", settings.venue or ""); row += 1
    write_meta_row(ws, row, "Организатор", settings.organizer or ""); row += 1
    row += 1

    for category in settings.categories:
        result = _calc_combined(db_path, category, teams)
        if result is None:
            continue
        category_teams, sp_pl, sp_pts, h2h_pl, h2h_pts, sl_pl, sl_pts, lr_pl, lr_pts, comb_pl, comb_pts = result

        ws.cell(row=row, column=1, value=_category_label(category)).font = XFont(bold=True, size=11)
        row += 1
        write_header_row(ws, row, COMBINED_COLS_XLSX); row += 1

        for team in sorted(category_teams, key=lambda t: (comb_pl.get(t.name, 9999), t.start_number)):
            main_m = [m for m in team.crew_members if m.role != "reserve"]
            lineup = "\n".join(f"{m.full_name}, {m.birth_date}, {m.rank}" for m in main_m) or ""
            write_data_row(ws, row, [
                team.start_number, team.name, lineup, team.region,
                sp_pl.get(team.name), sp_pts.get(team.name, 0),
                h2h_pl.get(team.name), h2h_pts.get(team.name, 0),
                sl_pl.get(team.name), sl_pts.get(team.name, 0),
                lr_pl.get(team.name), lr_pts.get(team.name, 0),
                comb_pl.get(team.name), comb_pts.get(team.name, 0),
            ], col_count=14)
            row += 1
        row += 1

    row += 1
    write_meta_row(ws, row, "Главный судья", _judge_name(judges.chief_judge)); row += 1
    write_meta_row(ws, row, "Главный секретарь", _judge_name(judges.chief_secretary))
    return workbook_bytes(wb)

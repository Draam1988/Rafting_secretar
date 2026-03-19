from __future__ import annotations
from pathlib import Path

from raftsecretary.domain.points import points_for_place
from raftsecretary.storage.competition_storage import load_competition_settings
from raftsecretary.storage.judges_storage import load_judges
from raftsecretary.storage.parallel_sprint_storage import (
    load_parallel_sprint_heats, load_parallel_sprint_heat_meta,
    load_parallel_sprint_lineup_flags,
)
from raftsecretary.storage.team_storage import load_teams
from raftsecretary.export.pdf_builder import (
    new_pdf, pdf_bytes, write_doc_header, write_category_header,
    write_table_header, write_table_row, write_table_row_multiline, write_footer,
)
from raftsecretary.export.xlsx_builder import (
    new_workbook, workbook_bytes, write_meta_row, write_header_row, write_data_row,
)
from raftsecretary.export.sprint_export import _fmt, _judge_name, _category_label, _lineup_text

H2H_COLS_PDF = [
    ("№", 8), ("Команда", 45), ("Состав", 55),
    ("Субъект", 35), ("Время", 18), ("Штраф", 18),
    ("Итог", 18), ("Место", 12), ("Очки", 12),
]
H2H_COLS_XLSX = [
    ("№", 6), ("Команда", 22), ("Состав", 35),
    ("Субъект", 20), ("Время", 10), ("Штраф", 10),
    ("Итог", 10), ("Место", 8), ("Очки", 8),
]


def _load_data(db_path: Path):
    settings = load_competition_settings(db_path)
    judges = load_judges(db_path)
    teams = load_teams(db_path)
    comp_dates = ", ".join(settings.competition_dates or [settings.competition_date])
    return settings, judges, teams, comp_dates


def _get_result(result_data, lane):
    base_time = penalty = total = ""
    if result_data is not None:
        entry, meta, result_lane = result_data
        total = _fmt(entry.total_time_seconds)
        if meta is not None:
            if result_lane == "left":
                base_time = _fmt(meta.left_base_time_seconds)
                penalty = _fmt(meta.left_penalty_seconds)
            else:
                base_time = _fmt(meta.right_base_time_seconds)
                penalty = _fmt(meta.right_penalty_seconds)
    return base_time, penalty, total


def build_parallel_sprint_pdf(db_path: Path) -> bytes:
    from raftsecretary.web.app import _parallel_sprint_ordered_names, _parallel_sprint_full_places_map, _parallel_sprint_last_result_data
    settings, judges, teams, comp_dates = _load_data(db_path)
    pdf = new_pdf()
    pdf.add_page()
    write_doc_header(pdf, "H2H (Параллельный спринт)", settings.name or "", comp_dates,
                     settings.venue or "", settings.organizer or "")

    for category in settings.categories:
        category_teams = [t for t in teams if t.category_key == category.key]
        heats = load_parallel_sprint_heats(db_path, category.key)
        if not category_teams and not heats:
            continue
        saved_by_round = {rn: (l, r) for rn, l, r in heats}
        heat_meta = load_parallel_sprint_heat_meta(db_path, category.key)
        lineup_flags = load_parallel_sprint_lineup_flags(db_path, category.key)
        ordered_names = _parallel_sprint_ordered_names(category_teams, saved_by_round)
        result_by_team = _parallel_sprint_last_result_data(saved_by_round, heat_meta)
        place_map = {name: i for i, name in enumerate(ordered_names, 1)}
        team_map = {t.name: t for t in category_teams}

        write_category_header(pdf, _category_label(category))
        write_table_header(pdf, H2H_COLS_PDF)
        for team_name in ordered_names:
            team = team_map.get(team_name)
            if not team:
                continue
            place = place_map.get(team_name)
            pts = points_for_place("parallel_sprint", place) if place else 0
            base_time, penalty, total = _get_result(result_by_team.get(team_name), None)
            lineup = _lineup_text(team, lineup_flags)
            write_table_row_multiline(
                pdf,
                cells_before=[
                    (str(team.start_number), 8),
                    (team.name, 45),
                ],
                multiline_text=lineup,
                multiline_width=55,
                cells_after=[
                    (team.region, 35),
                    (base_time, 18),
                    (penalty, 18),
                    (total, 18),
                    (str(place) if place else "", 12),
                    (str(pts), 12),
                ],
            )
        pdf.ln(3)

    write_footer(pdf, _judge_name(judges.chief_judge), _judge_name(judges.chief_secretary))
    return pdf_bytes(pdf)


def build_parallel_sprint_xlsx(db_path: Path) -> bytes:
    from openpyxl.styles import Font as XFont
    from raftsecretary.web.app import _parallel_sprint_ordered_names, _parallel_sprint_last_result_data
    settings, judges, teams, comp_dates = _load_data(db_path)
    wb, ws = new_workbook()
    ws.title = "H2H"

    row = 1
    write_meta_row(ws, row, "Соревнование", settings.name or ""); row += 1
    write_meta_row(ws, row, "Даты", comp_dates); row += 1
    write_meta_row(ws, row, "Место", settings.venue or ""); row += 1
    write_meta_row(ws, row, "Организатор", settings.organizer or ""); row += 1
    row += 1

    for category in settings.categories:
        category_teams = [t for t in teams if t.category_key == category.key]
        heats = load_parallel_sprint_heats(db_path, category.key)
        if not category_teams and not heats:
            continue
        saved_by_round = {rn: (l, r) for rn, l, r in heats}
        heat_meta = load_parallel_sprint_heat_meta(db_path, category.key)
        lineup_flags = load_parallel_sprint_lineup_flags(db_path, category.key)
        ordered_names = _parallel_sprint_ordered_names(category_teams, saved_by_round)
        result_by_team = _parallel_sprint_last_result_data(saved_by_round, heat_meta)
        place_map = {name: i for i, name in enumerate(ordered_names, 1)}
        team_map = {t.name: t for t in category_teams}

        ws.cell(row=row, column=1, value=_category_label(category)).font = XFont(bold=True, size=11)
        row += 1
        write_header_row(ws, row, H2H_COLS_XLSX); row += 1
        for team_name in ordered_names:
            team = team_map.get(team_name)
            if not team:
                continue
            place = place_map.get(team_name)
            pts = points_for_place("parallel_sprint", place) if place else 0
            base_time, penalty, total = _get_result(result_by_team.get(team_name), None)
            lineup = _lineup_text(team, lineup_flags)
            write_data_row(ws, row, [
                team.start_number, team.name, lineup, team.region,
                base_time, penalty, total, place, pts,
            ], col_count=9)
            row += 1
        row += 1

    row += 1
    write_meta_row(ws, row, "Главный судья", _judge_name(judges.chief_judge)); row += 1
    write_meta_row(ws, row, "Главный секретарь", _judge_name(judges.chief_secretary))
    return workbook_bytes(wb)

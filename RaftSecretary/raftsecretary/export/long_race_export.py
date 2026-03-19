from __future__ import annotations
from pathlib import Path

from raftsecretary.domain.sprint import SprintEntry, rank_sprint_entries
from raftsecretary.domain.points import points_for_place
from raftsecretary.storage.competition_storage import load_competition_settings
from raftsecretary.storage.judges_storage import load_judges
from raftsecretary.storage.long_race_storage import load_long_race_entries, load_long_race_lineup_flags
from raftsecretary.storage.team_storage import load_teams
from raftsecretary.export.pdf_builder import (
    new_pdf, pdf_bytes, write_doc_header, write_category_header,
    write_table_header, write_table_row, write_footer,
)
from raftsecretary.export.xlsx_builder import (
    new_workbook, workbook_bytes, write_meta_row, write_header_row, write_data_row,
)
from raftsecretary.export.sprint_export import _fmt, _judge_name, _category_label, _lineup_text, _normalize_status

LONG_RACE_COLS_PDF = [
    ("№ п/п", 10), ("№", 8), ("Команда", 40), ("Состав", 55),
    ("Субъект", 35), ("Вр. старта", 18), ("Время", 18),
    ("Штраф", 18), ("Место", 12), ("Очки", 12),
]
LONG_RACE_COLS_XLSX = [
    ("№ п/п", 8), ("№", 6), ("Команда", 22), ("Состав", 35),
    ("Субъект", 20), ("Вр. старта", 12), ("Время", 10),
    ("Штраф", 10), ("Место", 8), ("Очки", 8),
]


def _long_race_points(entry, place) -> int:
    if entry is None or getattr(entry, "status", "") != "OK":
        return 0
    return points_for_place("long_race", place) if place else 0


def _load_data(db_path: Path):
    settings = load_competition_settings(db_path)
    judges = load_judges(db_path)
    teams = load_teams(db_path)
    comp_dates = ", ".join(settings.competition_dates or [settings.competition_date])
    return settings, judges, teams, comp_dates


def _rows_for_category(db_path, category, teams):
    raw = load_long_race_entries(db_path, category.key)
    entries = [
        SprintEntry(
            team_name=e.team_name, start_order=e.start_order,
            base_time_seconds=e.base_time_seconds,
            buoy_penalty_seconds=e.buoy_penalty_seconds,
            behavior_penalty_seconds=e.behavior_penalty_seconds,
            status=_normalize_status(e.status),
            start_time=e.start_time,
        )
        for e in raw
    ]
    category_teams = [t for t in teams if t.category_key == category.key]
    if not category_teams and not entries:
        return None
    entry_by_team = {e.team_name: e for e in entries}
    ranked = rank_sprint_entries(entries)
    places = {e.team_name: i for i, e in enumerate(ranked, 1)}
    lineup_flags = load_long_race_lineup_flags(db_path, category.key)
    return category_teams, entry_by_team, places, lineup_flags


def build_long_race_pdf(db_path: Path) -> bytes:
    settings, judges, teams, comp_dates = _load_data(db_path)
    pdf = new_pdf()
    pdf.add_page()
    write_doc_header(pdf, "Длинная гонка", settings.name or "", comp_dates,
                     settings.venue or "", settings.organizer or "")

    for category in settings.categories:
        result = _rows_for_category(db_path, category, teams)
        if result is None:
            continue
        category_teams, entry_by_team, places, lineup_flags = result
        write_category_header(pdf, _category_label(category))
        write_table_header(pdf, LONG_RACE_COLS_PDF)
        for team in sorted(category_teams, key=lambda t: (places.get(t.name, 9999), t.start_number)):
            entry = entry_by_team.get(team.name)
            place = places.get(team.name)
            pts = _long_race_points(entry, place)
            start_order_text = "н/у" if entry and entry.start_order == 99 else (
                str(entry.start_order) if entry and entry.start_order else ""
            )
            lineup = _lineup_text(team, lineup_flags).replace("\n", "; ")
            write_table_row(pdf, [
                (start_order_text, 10), (str(team.start_number), 8),
                (team.name, 40), (lineup, 55), (team.region, 35),
                (entry.start_time if entry else "", 18),
                (_fmt(entry.base_time_seconds) if entry else "", 18),
                (_fmt(entry.behavior_penalty_seconds) if entry else "", 18),
                (str(place) if place else "", 12), (str(pts), 12),
            ])
        pdf.ln(3)

    write_footer(pdf, _judge_name(judges.chief_judge), _judge_name(judges.chief_secretary))
    return pdf_bytes(pdf)


def build_long_race_xlsx(db_path: Path) -> bytes:
    from openpyxl.styles import Font as XFont
    settings, judges, teams, comp_dates = _load_data(db_path)
    wb, ws = new_workbook()
    ws.title = "Длинная гонка"

    row = 1
    write_meta_row(ws, row, "Соревнование", settings.name or ""); row += 1
    write_meta_row(ws, row, "Даты", comp_dates); row += 1
    write_meta_row(ws, row, "Место", settings.venue or ""); row += 1
    write_meta_row(ws, row, "Организатор", settings.organizer or ""); row += 1
    row += 1

    for category in settings.categories:
        result = _rows_for_category(db_path, category, teams)
        if result is None:
            continue
        category_teams, entry_by_team, places, lineup_flags = result
        ws.cell(row=row, column=1, value=_category_label(category)).font = XFont(bold=True, size=11)
        row += 1
        write_header_row(ws, row, LONG_RACE_COLS_XLSX); row += 1
        for team in sorted(category_teams, key=lambda t: (places.get(t.name, 9999), t.start_number)):
            entry = entry_by_team.get(team.name)
            place = places.get(team.name)
            pts = _long_race_points(entry, place)
            start_order_text = "н/у" if entry and entry.start_order == 99 else (
                str(entry.start_order) if entry and entry.start_order else ""
            )
            lineup = _lineup_text(team, lineup_flags)
            write_data_row(ws, row, [
                start_order_text, team.start_number, team.name, lineup, team.region,
                entry.start_time if entry else "",
                _fmt(entry.base_time_seconds) if entry else "",
                _fmt(entry.behavior_penalty_seconds) if entry else "",
                place, pts,
            ], col_count=10)
            row += 1
        row += 1

    row += 1
    write_meta_row(ws, row, "Главный судья", _judge_name(judges.chief_judge)); row += 1
    write_meta_row(ws, row, "Главный секретарь", _judge_name(judges.chief_secretary))
    return workbook_bytes(wb)

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import random
from urllib.parse import parse_qs, quote, urlparse

from raftsecretary.domain.models import Category, Team, TeamMember
from raftsecretary.storage.competition_storage import load_competition_settings
from raftsecretary.storage.competition_storage import CompetitionSettingsRecord, save_competition_settings
from raftsecretary.storage.db import create_competition_db, delete_competition_db, list_competition_dbs
from raftsecretary.storage.judges_storage import (
    JudgeRecord,
    JudgesRecord,
    RequiredJudgeRecord,
    load_judges,
    save_judges,
)
from raftsecretary.storage.parallel_sprint_storage import (
    clear_parallel_sprint_protocol,
    clear_parallel_sprint_rounds,
    load_parallel_sprint_heats,
    load_parallel_sprint_heat_meta,
    load_parallel_sprint_lineup_flags,
    load_parallel_sprint_start_entries,
    ParallelSprintHeatMeta,
    save_parallel_sprint_heat,
    save_parallel_sprint_heat_meta,
    save_parallel_sprint_lineup_flags,
    save_parallel_sprint_start_entries,
)
from raftsecretary.storage.slalom_storage import (
    clear_slalom_category,
    load_slalom_lineup_flags,
    load_slalom_runs,
    save_slalom_lineup_flags,
    save_slalom_run,
)
from raftsecretary.storage.long_race_storage import (
    load_long_race_entries,
    load_long_race_lineup_flags,
    save_long_race_entries,
    save_long_race_lineup_flags,
)
from raftsecretary.storage.sprint_storage import (
    load_sprint_entries,
    load_sprint_lineup_flags,
    save_sprint_entries,
    save_sprint_lineup_flags,
)
from raftsecretary.storage.team_storage import load_teams, save_teams
from raftsecretary.domain.sprint import SprintEntry, rank_sprint_entries
from raftsecretary.domain.parallel_sprint import (
    ParallelSprintHeatResult,
    build_four_team_semifinals,
    build_second_stage_pairs,
    build_stage_one_matches,
    main_bracket_size,
    rank_eliminated_crews,
    resolve_heat_winner,
    resolve_four_team_places,
    second_stage_seed_order,
    split_direct_qualifiers_and_stage_one,
)
from raftsecretary.domain.slalom import SlalomRun, best_run_for_team
from raftsecretary.domain.combined import combine_points
from raftsecretary.domain.points import points_for_place

APP_VERSION = "v.0.1.6"
VERSION_DATE = "20.03.2026г."
APP_AUTHOR = "Павел Хохрин"
SPORT_RANK_OPTIONS = [
    "Б/Р",
    "МСМК",
    "МС",
    "КМС",
    "1 разряд",
    "2 разряд",
    "3 разряд",
    "1 юношеский",
    "2 юношеский",
    "3 юношеский",
]

PARALLEL_PENDING_TOTAL_SECONDS = 999999
JUDGE_CATEGORY_OPTIONS = [
    "Спортивный судья всероссийской категории",
    "Спортивный судья первой категории",
    "Спортивный судья второй категории",
    "Спортивный судья третьей категории",
    "Юный спортивный судья",
]

DISCIPLINE_LABELS = {
    "sprint": "Спринт",
    "parallel_sprint": "Параллельный спринт",
    "slalom": "Слалом",
    "long_race": "Длинная гонка",
}

CATEGORY_OPTIONS = [
    ("R4", "men", "U16", "R4 Мужчины U16"),
    ("R4", "women", "U16", "R4 Женщины U16"),
    ("R4", "men", "U20", "R4 Мужчины U20"),
    ("R4", "women", "U20", "R4 Женщины U20"),
    ("R4", "men", "U24", "R4 Мужчины U24"),
    ("R4", "women", "U24", "R4 Женщины U24"),
    ("R4", "men", "Cup", "R4 Кубок Мужчины"),
    ("R4", "women", "Cup", "R4 Кубок Женщины"),
    ("R4", "men", "Veterans", "R4 Ветераны Мужчины"),
    ("R4", "women", "Veterans", "R4 Ветераны Женщины"),
    ("R6", "men", "U16", "R6 Мужчины U16"),
    ("R6", "women", "U16", "R6 Женщины U16"),
    ("R6", "men", "U20", "R6 Мужчины U20"),
    ("R6", "women", "U20", "R6 Женщины U20"),
    ("R6", "men", "U24", "R6 Мужчины U24"),
    ("R6", "women", "U24", "R6 Женщины U24"),
    ("R6", "men", "Cup", "R6 Кубок Мужчины"),
    ("R6", "women", "Cup", "R6 Кубок Женщины"),
    ("R6", "men", "Veterans", "R6 Ветераны Мужчины"),
    ("R6", "women", "Veterans", "R6 Ветераны Женщины"),
]


@dataclass
class WebApp:
    data_dir: Path

    def handle(
        self,
        method: str,
        path: str,
        form_data: dict[str, str] | None = None,
    ) -> tuple[str, list[tuple[str, str]], str | bytes]:
        parsed = urlparse(path)
        route_path = parsed.path
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}

        if method == "GET" and route_path == "/":
            return self._home_response()
        if method == "GET" and route_path == "/competitions/delete":
            return self._delete_competition_confirmation_response(query)
        if method == "GET" and route_path == "/dashboard":
            return self._dashboard_response(query)
        if method == "GET" and route_path == "/faq":
            return self._faq_response()
        if method == "GET" and route_path == "/settings":
            return self._settings_response(query)
        if method == "GET" and route_path == "/judges":
            return self._judges_response(query)
        if method == "GET" and route_path == "/teams":
            return self._teams_response(query)
        if method == "GET" and route_path == "/teams/delete":
            return self._team_delete_confirmation_response(query)
        if method == "GET" and route_path == "/sprint":
            return self._sprint_response(query)
        if method == "GET" and route_path == "/parallel-sprint":
            return self._parallel_sprint_response(query)
        if method == "GET" and route_path == "/slalom":
            return self._slalom_response(query)
        if method == "GET" and route_path == "/long-race":
            return self._long_race_response(query)
        if method == "GET" and route_path == "/combined":
            return self._combined_response(query)
        if method == "GET" and route_path == "/export":
            return self._export_response(query)
        if method == "GET" and route_path == "/export/sprint-results":
            return self._sprint_results_protocol_response(query)
        if method == "GET" and route_path == "/export/slalom-results":
            return self._slalom_results_protocol_response(query)
        if method == "GET" and route_path == "/export/parallel-sprint-results":
            return self._parallel_sprint_results_protocol_response(query)
        if method == "GET" and route_path == "/export/long-race-results":
            return self._long_race_results_protocol_response(query)
        if method == "GET" and route_path == "/export/combined-results":
            return self._combined_results_protocol_response(query)
        if method == "GET" and route_path == "/export/sprint-results/pdf":
            return self._sprint_results_pdf_response(query)
        if method == "GET" and route_path == "/export/sprint-results/xlsx":
            return self._sprint_results_xlsx_response(query)
        if method == "GET" and route_path == "/export/slalom-results/pdf":
            return self._slalom_results_pdf_response(query)
        if method == "GET" and route_path == "/export/slalom-results/xlsx":
            return self._slalom_results_xlsx_response(query)
        if method == "GET" and route_path == "/export/parallel-sprint-results/pdf":
            return self._parallel_sprint_results_pdf_response(query)
        if method == "GET" and route_path == "/export/parallel-sprint-results/xlsx":
            return self._parallel_sprint_results_xlsx_response(query)
        if method == "GET" and route_path == "/export/long-race-results/pdf":
            return self._long_race_results_pdf_response(query)
        if method == "GET" and route_path == "/export/long-race-results/xlsx":
            return self._long_race_results_xlsx_response(query)
        if method == "GET" and route_path == "/export/combined-results/pdf":
            return self._combined_results_pdf_response(query)
        if method == "GET" and route_path == "/export/combined-results/xlsx":
            return self._combined_results_xlsx_response(query)
        if method == "POST" and route_path == "/settings/save":
            return self._save_settings_response(form_data or {})
        if method == "POST" and route_path == "/judges/save":
            return self._save_judges_response(form_data or {})
        if method == "POST" and route_path == "/teams/add":
            return self._add_team_response(form_data or {})
        if method == "POST" and route_path == "/teams/delete":
            return self._delete_team_response(form_data or {})
        if method == "POST" and route_path == "/sprint/save":
            return self._save_sprint_response(form_data or {})
        if method == "POST" and route_path == "/sprint/draw":
            return self._draw_sprint_response(form_data or {})
        if method == "POST" and route_path == "/sprint/lineup":
            return self._save_sprint_lineup_response(form_data or {})
        if method == "POST" and route_path == "/long-race/build":
            return self._build_long_race_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/save":
            return self._save_parallel_sprint_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/build":
            return self._build_parallel_sprint_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/clear":
            return self._clear_parallel_sprint_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/clear-stage":
            return self._clear_parallel_sprint_stage_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/start-list/save":
            return self._save_parallel_sprint_start_list_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/lineup":
            return self._save_parallel_sprint_lineup_response(form_data or {})
        if method == "POST" and route_path == "/parallel-sprint/result":
            return self._save_parallel_sprint_result_response(form_data or {})
        if method == "POST" and route_path == "/slalom/lineup":
            return self._save_slalom_lineup_response(form_data or {})
        if method == "POST" and route_path == "/slalom/clear":
            return self._clear_slalom_response(form_data or {})
        if method == "POST" and route_path == "/slalom/schedule":
            return self._schedule_slalom_response(form_data or {})
        if method == "POST" and route_path == "/slalom/save":
            return self._save_slalom_response(form_data or {})
        if method == "POST" and route_path == "/long-race/save":
            return self._save_long_race_response(form_data or {})
        if method == "POST" and route_path == "/long-race/lineup":
            return self._save_long_race_lineup_response(form_data or {})
        if method == "POST" and route_path == "/competitions":
            return self._create_competition_response(form_data or {})
        if method == "POST" and route_path == "/competitions/delete":
            return self._delete_competition_response(form_data or {})
        return ("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], "Not found")

    def _home_response(self) -> tuple[str, list[tuple[str, str]], str]:
        db_files = list_competition_dbs(self.data_dir)
        latest_db = db_files[-1].name if db_files else ""
        archive_items = (
            "".join(
                f"""
<div class="ledger-row">
  <a class="ledger-link" href="/dashboard?db={escape(path.name)}">{escape(_display_competition_name(path.name))}</a>
  <a class="delete-link" href="/competitions/delete?db={quote(path.name)}">УДАЛИТЬ</a>
</div>
"""
                for path in db_files
            )
            or '<p style="padding:18px 16px; color:var(--muted); font-style:italic;">Соревнований пока нет</p>'
        )
        open_last_href = (
            f"/dashboard?db={escape(latest_db)}" if latest_db else "#"
        )
        body = _page(
            "RaftSecretary",
            f"""
<div class="index-hero">
  <div>
    <h1>RaftSecretary</h1>
  </div>
  <div class="index-meta">
    <span class="ver">{APP_VERSION} &middot; {VERSION_DATE}</span>
    <span class="author">Автор: {APP_AUTHOR}</span>
  </div>
</div>
<div class="index-open-last">
  <a class="stitch-cta" href="{open_last_href}">Открыть последнее соревнование</a>
</div>
<div class="index-layout" style="margin-top:40px;">
  <section>
    <p class="section-label">Архив файлов соревнований</p>
    <div class="ledger-archive">{archive_items}</div>
  </section>
  <section>
    <div class="form-panel">
      <h3>Новое соревнование</h3>
      <form method="post" action="/competitions">
        <div class="form-field">
          <label for="filename">Имя файла (.db)</label>
          <input id="filename" name="filename" class="editorial-input" placeholder="Введите название..." autocomplete="off" />
        </div>
        <button class="stitch-cta" type="submit" style="display:block; width:100%; text-align:center; padding:12px 0; background:var(--panel2); margin-bottom:0;">Создать файл</button>
      </form>
      <p class="form-hint">База данных будет создана в рабочем каталоге приложения.</p>
    </div>
    <div style="margin-top:20px; display:flex; gap:8px; flex-wrap:wrap;">
      <a class="stitch-cta" href="/faq">F.A.Q.</a>
      <a class="stitch-cta" href="#">VK</a>
      <a class="stitch-cta" href="#">TG</a>
    </div>
  </section>
</div>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _faq_response(self) -> tuple[str, list[tuple[str, str]], str]:
        body = _page(
            "F.A.Q.",
            """
<section class="panel-page narrow">
  <div class="page-head">
    <div>
      <p class="eyebrow">F.A.Q.</p>
      <h1>Инструкция</h1>
      <p class="subtle">Раздел пока пустой.</p>
    </div>
    <a class="secondary-link" href="/">На стартовый экран</a>
  </div>
  <section class="panel-card">
    <p class="subtle">Здесь позже появятся инструкции по работе с приложением.</p>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _dashboard_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = load_teams(db_path)
        judges_record = load_judges(db_path)
        judges_status, judges_detail = _judges_status(judges_record)
        blocks = [
            ("Соревнование", f"/settings?db={escape(db_name)}", "ok" if settings.name else "warn", settings.name or "Не настроено"),
            ("Судьи", f"/judges?db={escape(db_name)}", judges_status, judges_detail),
            ("Команды", f"/teams?db={escape(db_name)}", "ok" if teams else "warn", f"{len(teams)} команд"),
            ("Протоколы", f"/export?db={escape(db_name)}", "danger", "Еще не реализовано"),
        ]
        discipline_blocks = []
        if "sprint" in settings.enabled_disciplines:
            discipline_blocks.append(("Спринт", _first_category_link("/sprint", db_name, settings), "ok" if _has_any_sprint(db_path, settings) else "warn", "Результаты"))
        if "parallel_sprint" in settings.enabled_disciplines:
            discipline_blocks.append(("Параллельный спринт", _first_category_link("/parallel-sprint", db_name, settings), "ok" if _has_any_parallel(db_path, settings) else "warn", "Сетка"))
        if "slalom" in settings.enabled_disciplines:
            discipline_blocks.append(("Слалом", _first_category_link("/slalom", db_name, settings), "ok" if _has_any_slalom(db_path, settings) else "warn", "Попытки"))
        if "long_race" in settings.enabled_disciplines:
            discipline_blocks.append(("Длинная гонка", _first_category_link("/long-race", db_name, settings), "ok" if _has_any_long_race(db_path, settings) else "warn", "Результаты"))
        blocks = blocks[:3] + discipline_blocks + blocks[3:]
        cards = "".join(
            f"""
<a class="workspace-card {status}" href="{href}">
  <div class="workspace-head">
    <h2>{title}</h2>
    <span class="status-pill {status}">{_status_label(status)}</span>
  </div>
  <p>{escape(detail)}</p>
</a>
"""
            for title, href, status, detail in blocks
        )
        body = _page(
            "Рабочий стол секретаря",
            f"""
<section class="hero compact">
  <div>
    <p class="eyebrow">Рабочий стол секретаря</p>
    <h1>{escape(settings.name or db_name)}</h1>
    <p class="subtle">{escape(settings.competition_date or "Дата не указана")}</p>
  </div>
  <div class="meta">
    <p><a class="secondary-link" href="/">На стартовый экран</a></p>
    <p><strong>Файл</strong> {escape(db_name)}</p>
  </div>
</section>
<section class="workspace-grid">
  {cards}
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _create_competition_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        filename = _normalize_filename(form_data.get("filename", "competition"))
        db_path = create_competition_db(self.data_dir / f"{filename}.db")
        location = f"/dashboard?db={quote(db_path.name)}"
        return ("303 See Other", [("Location", location)], "")

    def _delete_competition_confirmation_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        display_name = _display_competition_name(db_name)
        body = _page(
            "Удаление соревнования",
            f"""
<section class="panel-page narrow">
  <div class="page-head">
    <div>
      <p class="eyebrow">Удаление</p>
      <h1>Удалить соревнование</h1>
      <p class="subtle">Это действие удалит файл соревнования без возможности восстановления.</p>
    </div>
    <a class="secondary-link" href="/">Отмена</a>
  </div>
  <section class="panel-card">
    <p class="confirm-text">Удалить соревнование <strong>{escape(display_name)}</strong>?</p>
    <form method="post" action="/competitions/delete" class="confirm-actions">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="confirm" value="yes" />
      <button type="submit" class="danger-button">Удалить</button>
      <a class="secondary-link" href="/">Отмена</a>
    </form>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _delete_competition_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        if form_data.get("confirm") == "yes":
            delete_competition_db(self.data_dir, db_name)
        return ("303 See Other", [("Location", "/")], "")

    def _settings_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        competition_days = settings.competition_dates or ([_first_competition_day(settings)] if _first_competition_day(settings) else [""])
        date_inputs = "".join(
            f'<label>Дата <input name="competition_date_{index}" type="date" value="{escape(day)}" /></label>'
            for index, day in enumerate(competition_days, start=1)
        )
        organizer_rows_src = settings.organizers if settings.organizers else ([settings.organizer] if settings.organizer else [""])
        organizer_inputs = "".join(
            f'<div class="organizer-row"><input name="organizer_{index}" value="{escape(org)}" placeholder="Название организации" />'
            f'<button type="button" class="remove-item-btn" onclick="this.closest(\'.organizer-row\').remove()" title="Удалить">×</button></div>'
            for index, org in enumerate(organizer_rows_src, start=1)
        )
        visible_dates = ", ".join(settings.competition_dates) or settings.competition_date or "Не указаны"
        discipline_controls = "".join(
            f"""
<label class="option-row">
  <input type="checkbox" name="discipline_{key}" {"checked" if key in settings.enabled_disciplines else ""} />
  <span>{label}</span>
</label>
"""
            for key, label in DISCIPLINE_LABELS.items()
        )
        selected_categories = {category.key for category in settings.categories}
        category_controls = "".join(
            f"""
<label class="option-row">
  <input type="checkbox" name="category__{boat_class}__{sex}__{age_group}" {"checked" if f"{boat_class}:{sex}:{age_group}" in selected_categories else ""} />
  <span>{label}</span>
</label>
"""
            for boat_class, sex, age_group, label in CATEGORY_OPTIONS
        )
        current_disciplines = ", ".join(
            DISCIPLINE_LABELS.get(key, key) for key in settings.enabled_disciplines
        ) or "Не выбраны"
        current_categories = ", ".join(
            _category_label(category) for category in settings.categories
        ) or "Не выбраны"
        discipline_summary = f"{len(settings.enabled_disciplines)} выбрано"
        category_summary = f"{len(settings.categories)} выбрано"
        body = _page(
            "Настройки соревнования",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">Соревнование</p>
      <h1>Настройки соревнования</h1>
      <p class="subtle">Основные параметры события, дисциплины и базовые настройки.</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <div class="panel-grid">
    <section class="panel-card">
      <h2>Основные данные</h2>
      <form method="post" action="/settings/save" class="stack-form">
        <input type="hidden" name="db" value="{escape(db_name)}" />
        <label>Название <input name="name" value="{escape(settings.name)}" /></label>
        <div class="date-stack">
          <div class="section-head compact-head">
            <label>Организаторы</label>
            <button type="button" class="secondary-link card-button" onclick="addOrganizer()">+ Добавить</button>
          </div>
          <div id="organizers-list">
            {organizer_inputs}
          </div>
          <template id="organizer-template">
            <div class="organizer-row"><input name="organizer___INDEX__" placeholder="Название организации" /><button type="button" class="remove-item-btn" onclick="this.closest('.organizer-row').remove()" title="Удалить">×</button></div>
          </template>
        </div>
        <label>Место проведения <input name="venue" value="{escape(settings.venue)}" /></label>
        <div class="date-stack">
          <div class="section-head compact-head">
            <div>
              <label>Даты соревнований</label>
            </div>
            <button type="button" class="secondary-link card-button" onclick="addCompetitionDay()">+ Добавить день</button>
          </div>
          <div id="competition-days" class="date-stack">
            {date_inputs}
          </div>
          <template id="competition-day-template">
            <label>Дата <input type="date" name="competition_date___INDEX__" /></label>
          </template>
        </div>
        <label>Описание <input name="description" value="{escape(settings.description)}" /></label>
        <label>Ворота слалома <input name="slalom_gate_count" value="{settings.slalom_gate_count}" /></label>
        <details class="inner-block">
          <summary>Дисциплины <span class="summary-note">{discipline_summary}</span></summary>
          <div class="options-grid">{discipline_controls}</div>
        </details>
        <details class="inner-block">
          <summary>Категории <span class="summary-note">{category_summary}</span></summary>
          <div class="options-grid">{category_controls}</div>
        </details>
        <button type="submit">Сохранить настройки</button>
      </form>
    </section>
    <section class="panel-card">
      <h2>Текущее состояние</h2>
      <dl class="info-list">
        <div><dt>Название</dt><dd>{escape(settings.name or "Не указано")}</dd></div>
        <div><dt>Организатор</dt><dd>{escape(settings.organizer or "Не указан")}</dd></div>
        <div><dt>Место проведения</dt><dd>{escape(settings.venue or "Не указано")}</dd></div>
        <div><dt>Даты</dt><dd>{escape(visible_dates)}</dd></div>
        <div><dt>Описание</dt><dd>{escape(settings.description or "Нет")}</dd></div>
        <div><dt>Дисциплины</dt><dd>{escape(current_disciplines)}</dd></div>
        <div><dt>Категории</dt><dd>{escape(current_categories)}</dd></div>
        <div><dt>Ворота слалома</dt><dd>{settings.slalom_gate_count}</dd></div>
      </dl>
    </section>
  </div>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _judges_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        record = load_judges(db_path)
        status, detail = _judges_status(record)
        role_cards = "".join(
            _required_judge_card(title, prefix, judge)
            for title, prefix, judge in [
                ("Главный судья соревнований", "chief_judge", record.chief_judge),
                ("Главный секретарь соревнований", "chief_secretary", record.chief_secretary),
                ("Начальник дистанции", "course_chief", record.course_chief),
            ]
        )
        judge_cards = record.judges or [JudgeRecord("", "", "", "")]
        judge_cards_html = "".join(
            _judge_card(index, judge)
            for index, judge in enumerate(judge_cards, start=1)
        )
        body = _page(
            "Судейский состав",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">Судьи</p>
      <h1>Судейский состав</h1>
      <p class="subtle">Реестр официальных лиц соревнований.</p>
    </div>
    <a class="stitch-cta" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <div class="panel-card" style="margin-top:4px;">
    <form method="post" action="/judges/save">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <div class="judges-section">
        <div class="judges-section-head">
          <h2>Ключевые позиции</h2>
          <span class="judges-section-note">обязательно для заполнения &nbsp; <span class="status-pill {status}">{escape(detail)}</span></span>
        </div>
        <div class="judges-required-grid">
          {role_cards}
        </div>
      </div>
      <div class="judges-section">
        <div class="judges-section-head">
          <h2>Судейская коллегия</h2>
          <span class="judges-section-note">дополнительные члены</span>
        </div>
        <div id="judges-list" class="judges-extra-list">
          {judge_cards_html}
        </div>
        <template id="judge-card-template">
          {_judge_card("__INDEX__", JudgeRecord("", "", "", ""))}
        </template>
        <button type="button" class="judges-add-btn" onclick="addJudgeCard()">+ Добавить судью</button>
      </div>
      <div class="judges-footer">
        <div class="judges-status-line">
          <span class="judges-status-dot"></span>
          <span>Локальное хранилище · офлайн режим</span>
        </div>
        <button type="submit" class="stitch-save-btn">Сохранить судейский состав</button>
      </div>
    </form>
  </div>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _teams_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = load_teams(db_path)
        editing_category = query.get("edit_category", "")
        editing_number = int(query.get("edit_number", "0") or 0)
        open_category = query.get("open_category", "")
        teams_by_category: dict[str, list[Team]] = {category.key: [] for category in settings.categories}
        for team in teams:
            teams_by_category.setdefault(team.category_key, []).append(team)
        category_sections = "".join(
            _team_category_block(
                db_name,
                category,
                teams_by_category.get(category.key, []),
                _editing_team_for_category(teams_by_category.get(category.key, []), editing_category, editing_number, category.key),
                _first_competition_day(settings),
                open_category or editing_category,
            )
            for category in settings.categories
        ) or """
<section class="panel-card">
  <h2>Категории не выбраны</h2>
  <p class="subtle">Сначала настройте категории в блоке `Соревнование`.</p>
</section>
"""
        body = _page(
            "Команды",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <h1>Команды</h1>
      <p class="subtle">Добавление участников соревнований</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <div class="category-stack">
    {category_sections}
  </div>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _sprint_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        category_key = query.get("category", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = load_teams(db_path)
        open_team = query.get("open_team", "").strip()
        saved_entries = load_sprint_entries(db_path, category_key)
        lineup_flags = load_sprint_lineup_flags(db_path, category_key)
        entry_by_team = {entry.team_name: entry for entry in saved_entries}
        ranked_entries = rank_sprint_entries(saved_entries)
        places_by_team = {entry.team_name: index for index, entry in enumerate(ranked_entries, start=1)}
        available_categories = "".join(
            (
                f"<li><strong>{escape(category.key)}</strong></li>"
                if category.key == category_key
                else f"<li><a href=\"/sprint?db={escape(db_name)}&category={escape(category.key)}\">{escape(category.key)}</a></li>"
            )
            for category in settings.categories
        ) or "<li>Категории не настроены</li>"
        available_teams = [
            team for team in teams if team.category_key == category_key
        ]
        rows = "".join(
            _sprint_table_row(
                index,
                db_name,
                category_key,
                team,
                entry_by_team.get(team.name),
                places_by_team.get(team.name),
                _resolve_sprint_lineup(team, lineup_flags.get(team.name, {})),
                open_team == team.name,
            )
            for index, team in enumerate(sorted(available_teams, key=lambda team: (entry_by_team.get(team.name).start_order if entry_by_team.get(team.name) else 9999, team.start_number, team.name)), start=1)
        ) or '<tr><td colspan="10">Для этой категории команд пока нет</td></tr>'
        body = _page(
            "Спринт",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">Спринт</p>
      <h1>Стартовый протокол</h1>
      <p class="subtle">{escape(category_key or 'Категория не выбрана')}</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <section class="panel-card">
    <div class="section-head">
      <div>
        <h2>Категории</h2>
        <ul class="compact-list">{available_categories}</ul>
      </div>
    </div>
    <div class="sprint-draw-card">
      <p class="section-label" style="margin-bottom:16px;">Жеребьёвка</p>
      <form method="post" action="/sprint/draw">
        <input type="hidden" name="db" value="{escape(db_name)}" />
        <input type="hidden" name="category_key" value="{escape(category_key)}" />
        <div class="sprint-draw-grid">
          <div class="draw-field">
            <span>Время первого старта</span>
            <input class="inline-time" data-time-mask="hhmm" name="draw_start_time" value="10:00" placeholder="10:00" />
          </div>
          <div class="draw-field">
            <span>Интервал</span>
            <input class="inline-time" data-time-mask="hhmm" name="draw_interval" value="00:02" placeholder="00:02" />
          </div>
          <div class="draw-actions">
            <button type="submit" class="stitch-cta">Провести жеребьевку</button>
            <button type="submit" class="stitch-cta" name="redraw" value="1">Пережеребить</button>
          </div>
        </div>
      </form>
    </div>
    <form method="post" action="/sprint/save" class="stack-form">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="category_key" value="{escape(category_key)}" />
      <table class="protocol-table">
        <thead>
          <tr>
            <th class="col-pp">№ п/п</th>
            <th class="col-time">Время<br />старта</th>
            <th>Команда</th>
            <th class="col-number">№</th>
            <th>Состав</th>
            <th>Субъект</th>
            <th class="col-time">Время</th>
            <th class="col-time">Штраф</th>
            <th class="col-place">Место</th>
            <th class="col-status">Статус</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <div class="sprint-footer">
        <p class="order-conflict-hint" style="margin:0;">Исправьте дублирующиеся номера старта перед сохранением</p>
        <button type="submit" class="stitch-save-btn">Сохранить протокол спринта</button>
      </div>
    </form>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _save_settings_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        db_path = self.data_dir / db_name
        disciplines = [
            key.removeprefix("discipline_")
            for key in DISCIPLINE_LABELS
            if form_data.get(f"discipline_{key}") == "on"
        ]
        categories = []
        for boat_class, sex, age_group, _label in CATEGORY_OPTIONS:
            field_name = f"category__{boat_class}__{sex}__{age_group}"
            if form_data.get(field_name) == "on":
                categories.append(
                    Category(boat_class=boat_class, sex=sex, age_group=age_group)
                )
        organizers = _organizers_from_form(form_data)
        save_competition_settings(
            db_path,
            CompetitionSettingsRecord(
                name=form_data.get("name", "").strip(),
                competition_date=", ".join(_competition_dates_from_form(form_data)),
                description=form_data.get("description", "").strip(),
                organizer=", ".join(organizers),
                organizers=organizers,
                venue=form_data.get("venue", "").strip(),
                enabled_disciplines=disciplines,
                categories=categories,
                slalom_gate_count=int(form_data.get("slalom_gate_count", "8") or 8),
                competition_dates=_competition_dates_from_form(form_data),
            ),
        )
        return ("303 See Other", [("Location", f"/settings?db={quote(db_name)}")], "")

    def _add_team_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        db_path = self.data_dir / db_name
        existing = load_teams(db_path)
        athletes = [
            value.strip()
            for value in form_data.get("athletes", "").split(",")
            if value.strip()
        ]
        members = _team_members_from_form(form_data)
        editing_category_key = form_data.get("editing_category_key", "").strip()
        editing_start_number = int(form_data.get("editing_start_number", "0") or 0)
        existing = [
            team
            for team in existing
            if not (
                editing_category_key
                and team.category_key == editing_category_key
                and team.start_number == editing_start_number
            )
        ]
        existing.append(
            Team(
                name=form_data.get("name", "").strip(),
                region=form_data.get("region", "").strip(),
                club=form_data.get("club", "").strip(),
                representative_full_name=form_data.get("representative_full_name", "").strip(),
                boat_class=form_data.get("boat_class", "").strip(),
                sex=form_data.get("sex", "").strip(),
                age_group=form_data.get("age_group", "").strip(),
                start_number=int(form_data.get("start_number", "0") or 0),
                athletes=athletes,
                members=members,
            )
        )
        save_teams(db_path, existing)
        category_key = Category(
            boat_class=form_data.get("boat_class", "").strip(),
            sex=form_data.get("sex", "").strip(),
            age_group=form_data.get("age_group", "").strip(),
        ).key
        return (
            "303 See Other",
            [("Location", f"/teams?db={quote(db_name)}&open_category={quote(category_key)}#{('category-' + category_key.replace(':', '-'))}")],
            "",
        )

    def _team_delete_confirmation_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        category_key = query.get("category", "")
        start_number = int(query.get("start_number", "0") or 0)
        db_path = self.data_dir / db_name
        team = next(
            (
                saved_team
                for saved_team in load_teams(db_path)
                if saved_team.category_key == category_key and saved_team.start_number == start_number
            ),
            None,
        )
        team_name = team.name if team else f"№ {start_number}"
        body = _page(
            "Удаление команды",
            f"""
<section class="panel-page narrow">
  <div class="page-head">
    <div>
      <p class="eyebrow">Команды</p>
      <h1>Удалить команду</h1>
      <p class="subtle">Команда будет удалена из категории без возможности восстановления.</p>
    </div>
    <a class="secondary-link" href="/teams?db={escape(db_name)}">Отмена</a>
  </div>
  <section class="panel-card">
    <p class="confirm-text">Удалить команду <strong>{escape(team_name)}</strong>?</p>
    <form method="post" action="/teams/delete" class="confirm-actions">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="category_key" value="{escape(category_key)}" />
      <input type="hidden" name="start_number" value="{start_number}" />
      <input type="hidden" name="confirm" value="yes" />
      <button type="submit" class="danger-button">Удалить</button>
      <a class="secondary-link" href="/teams?db={escape(db_name)}">Отмена</a>
    </form>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _delete_team_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        db_path = self.data_dir / db_name
        if form_data.get("confirm") == "yes":
            category_key = form_data.get("category_key", "")
            start_number = int(form_data.get("start_number", "0") or 0)
            filtered = [
                team
                for team in load_teams(db_path)
                if not (team.category_key == category_key and team.start_number == start_number)
            ]
            save_teams(db_path, filtered)
        return ("303 See Other", [("Location", f"/teams?db={quote(db_name)}")], "")

    def _save_judges_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        db_path = self.data_dir / db_name
        record = JudgesRecord(
            chief_judge=_required_judge_from_form(form_data, "chief_judge"),
            chief_secretary=_required_judge_from_form(form_data, "chief_secretary"),
            course_chief=_required_judge_from_form(form_data, "course_chief"),
            judges=_judges_from_form(form_data),
        )
        save_judges(db_path, record)
        return ("303 See Other", [("Location", f"/judges?db={quote(db_name)}")], "")

    def _save_sprint_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        row_indexes = sorted(
            {
                int(key.split("_")[1])
                for key in form_data
                if key.startswith("row_") and key.endswith("_team_name")
            }
        )
        entries: list[SprintEntry] = []
        for index in row_indexes:
            team_name = form_data.get(f"row_{index}_team_name", "").strip()
            if not team_name:
                continue
            entries.append(
                SprintEntry(
                    team_name=team_name,
                    start_order=int(form_data.get(f"row_{index}_start_order", "0") or 0),
                    start_time=form_data.get(f"row_{index}_start_time", "").strip(),
                    base_time_seconds=_parse_mmss(form_data.get(f"row_{index}_base_time_seconds", "0")),
                    buoy_penalty_seconds=0,
                    behavior_penalty_seconds=_parse_mmss(form_data.get(f"row_{index}_behavior_penalty_seconds", "0")),
                    status="Н/СТ"
                    if int(form_data.get(f"row_{index}_start_order", "0") or 0) == 99
                    else _normalize_sprint_status(form_data.get(f"row_{index}_status", "OK").strip() or "OK"),
                )
            )
        save_sprint_entries(db_path, category_key, entries)
        return ("303 See Other", [("Location", f"/sprint?db={quote(db_name)}&category={quote(category_key)}&saved=1")], "")

    def _draw_sprint_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        teams = [team for team in load_teams(db_path) if team.category_key == category_key]
        saved_entries = {entry.team_name: entry for entry in load_sprint_entries(db_path, category_key)}
        shuffled = list(teams)
        random.shuffle(shuffled)
        draw_start_time = form_data.get("draw_start_time", "10:00").strip() or "10:00"
        draw_interval = form_data.get("draw_interval", "00:02").strip() or "00:02"
        base_minutes = _parse_hhmm(draw_start_time)
        interval_minutes = _parse_hhmm(draw_interval)
        entries: list[SprintEntry] = []
        for index, team in enumerate(shuffled, start=1):
            current = saved_entries.get(team.name)
            entries.append(
                SprintEntry(
                    team_name=team.name,
                    start_order=index,
                    start_time=_format_hhmm(base_minutes + (index - 1) * interval_minutes),
                    base_time_seconds=current.base_time_seconds if current else 0,
                    buoy_penalty_seconds=0,
                    behavior_penalty_seconds=current.behavior_penalty_seconds if current else 0,
                    status=_normalize_sprint_status(current.status if current else "OK"),
                )
            )
        save_sprint_entries(db_path, category_key, entries)
        return ("303 See Other", [("Location", f"/sprint?db={quote(db_name)}&category={quote(category_key)}&saved=1")], "")

    def _save_sprint_lineup_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        lineup_target = form_data.get("lineup_target", "").strip()
        team_name, member_order, make_active = _parse_lineup_target(lineup_target)
        db_path = self.data_dir / db_name
        teams = load_teams(db_path)
        lineup_flags = load_sprint_lineup_flags(db_path, category_key)
        if not team_name:
            team_name = form_data.get("team_name", "").strip()
        team = next(
            (saved_team for saved_team in teams if saved_team.category_key == category_key and saved_team.name == team_name),
            None,
        )
        if team is not None and member_order <= 0:
            member_full_name = form_data.get("member_full_name", "").strip()
            if member_full_name:
                for index, member in enumerate(team.crew_members, start=1):
                    if member.full_name == member_full_name:
                        member_order = index
                        break
            make_active = form_data.get("active", "0") == "1"
        if team is not None and member_order > 0:
            current_flags = _resolve_sprint_lineup(team, lineup_flags.get(team.name, {}))
            updated_flags = {
                member["member_order"]: member["is_active"]  # type: ignore[index]
                for member in current_flags
            }
            updated_flags[member_order] = make_active
            lineup_flags[team.name] = updated_flags
            save_sprint_lineup_flags(db_path, category_key, lineup_flags)
        return (
            "303 See Other",
            [("Location", f"/sprint?db={quote(db_name)}&category={quote(category_key)}")],
            "",
        )

    def _parallel_sprint_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        category_key = query.get("category", "")
        open_team = query.get("open_team", "").strip()
        open_result = query.get("open_result", "").strip()
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = load_teams(db_path)
        sprint_entries = rank_sprint_entries(load_sprint_entries(db_path, category_key))
        sprint_order = [entry.team_name for entry in sprint_entries]
        saved_start_entries = load_parallel_sprint_start_entries(db_path, category_key)
        saved_by_team = {entry.team_name: entry for entry in saved_start_entries}
        heat_meta = load_parallel_sprint_heat_meta(db_path, category_key)
        saved_by_round = {
            round_name: (left, right)
            for round_name, left, right in load_parallel_sprint_heats(db_path, category_key)
        }
        lineup_flags = load_parallel_sprint_lineup_flags(db_path, category_key)
        category_teams = [team for team in teams if team.category_key == category_key]
        team_map = {team.name: team for team in category_teams}
        ordered_teams = [team_map[name] for name in sprint_order if name in team_map]
        seeded_team_names = [team.name for team in ordered_teams]
        available_categories = "".join(
            (
                f"<li><strong>{escape(category.key)}</strong></li>"
                if category.key == category_key
                else f"<li><a href=\"/parallel-sprint?db={escape(db_name)}&category={escape(category.key)}\">{escape(category.key)}</a></li>"
            )
            for category in settings.categories
        ) or "<li>Категории не настроены</li>"
        start_nodes = "".join(
            _parallel_sprint_start_node_html(
                index=index,
                db_name=db_name,
                category_key=category_key,
                team=team,
                entry=saved_by_team.get(team.name),
                is_open=open_team == team.name,
            )
            for index, team in enumerate(ordered_teams, start=1)
        ) or '<div class="subtle">Для H2H пока не хватает результатов спринта.</div>'
        open_result_panel = _parallel_sprint_result_panel_html(
            db_name,
            category_key,
            seeded_team_names,
            open_result,
            heat_meta,
            saved_by_round,
            team_map,
            saved_by_team,
        )
        columns = _parallel_sprint_preview_columns_html(
            db_name,
            category_key,
            ordered_teams,
            saved_by_team,
            sprint_order,
            heat_meta,
            saved_by_round,
            team_map,
            _parallel_sprint_open_result_round_title(seeded_team_names, open_result),
            open_result_panel,
        )
        open_team_panel = ""
        if open_team and open_team in team_map:
            open_team_panel = _parallel_sprint_lineup_panel_html(
                db_name,
                category_key,
                team_map[open_team],
                _resolve_sprint_lineup(team_map[open_team], lineup_flags.get(open_team, {})),
            )
        standings_panel = _parallel_sprint_standings_panel_html(
            ordered_teams,
            heat_meta,
            saved_by_round,
        )
        body = _page(
            "H2H",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">H2H</p>
      <h1>Стартовый протокол</h1>
      <p class="subtle">{escape(category_key or 'Категория не выбрана')}</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <section class="panel-card">
    <div class="section-head">
      <div>
        <h2>Категории</h2>
        <ul class="compact-list">{available_categories}</ul>
      </div>
      <form method="post" action="/parallel-sprint/build" class="team-actions">
        <input type="hidden" name="db" value="{escape(db_name)}" />
        <input type="hidden" name="category_key" value="{escape(category_key)}" />
        <label>Время старта <input class="inline-time" data-time-mask="hhmm" name="draw_start_time" value="10:00" placeholder="10:00" /></label>
        <label>Интервал <input class="inline-time" data-time-mask="hhmm" name="draw_interval" value="00:02" placeholder="00:02" /></label>
        <button type="submit" class="stitch-cta">Сформировать старт</button>
      </form>
      <form method="post" action="/parallel-sprint/clear" class="team-actions" onsubmit="return confirm('Очистить весь протокол H2H для этой категории?');">
        <input type="hidden" name="db" value="{escape(db_name)}" />
        <input type="hidden" name="category_key" value="{escape(category_key)}" />
        <button type="submit" class="secondary-link danger-link">Очистить протокол</button>
      </form>
    </div>
  </section>
  <section class="panel-card">
    <h2>Все участники категории</h2>
    <p class="subtle">{escape(_parallel_sprint_rules_hint(len(ordered_teams)))}</p>
    <div class="h2h-board">
      <section class="h2h-column h2h-start-column">
        <h2>Старт</h2>
        <form method="post" action="/parallel-sprint/start-list/save" class="stack-form">
          <input type="hidden" name="db" value="{escape(db_name)}" />
          <input type="hidden" name="category_key" value="{escape(category_key)}" />
          <div class="h2h-column-body">{start_nodes}</div>
          <button type="submit" class="stitch-save-btn">Сохранить стартовый список H2H</button>
        </form>
      </section>
      {columns}
      {standings_panel}
    </div>
  </section>
  {open_team_panel}
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _save_parallel_sprint_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        left_base_time_seconds = _parse_mmss(form_data.get("left_base_time_seconds", "0"))
        right_base_time_seconds = _parse_mmss(form_data.get("right_base_time_seconds", "0"))
        left_penalty_seconds, right_penalty_seconds = _parallel_penalties_from_pattern(
            form_data.get("buoy_penalty_pattern", "0/0").strip() or "0/0"
        )
        left_result = ParallelSprintHeatResult(
            team_name=form_data.get("left_team_name", "").strip(),
            lane="left",
            start_order=int(form_data.get("left_start_order", "0") or 0),
            total_time_seconds=left_base_time_seconds + left_penalty_seconds,
            missed_buoys=0,
            status=_normalize_sprint_status(form_data.get("left_status", "OK").strip() or "OK"),
        )
        right_result = ParallelSprintHeatResult(
            team_name=form_data.get("right_team_name", "").strip(),
            lane="right",
            start_order=int(form_data.get("right_start_order", "0") or 0),
            total_time_seconds=right_base_time_seconds + right_penalty_seconds,
            missed_buoys=0,
            status=_normalize_sprint_status(form_data.get("right_status", "OK").strip() or "OK"),
        )
        winner_team_name = resolve_heat_winner(left_result, right_result).team_name if left_result.team_name and right_result.team_name else ""
        save_parallel_sprint_heat(
            db_path=db_path,
            category_key=category_key,
            round_name=form_data.get("round_name", "").strip(),
            left=left_result,
            right=right_result,
        )
        round_name = form_data.get("round_name", "").strip()
        save_parallel_sprint_heat_meta(
            db_path=db_path,
            category_key=category_key,
            meta=ParallelSprintHeatMeta(
                round_name=round_name,
                scheduled_start_time=form_data.get("scheduled_start_time", "").strip(),
                left_base_time_seconds=left_base_time_seconds,
                left_penalty_seconds=left_penalty_seconds,
                right_base_time_seconds=right_base_time_seconds,
                right_penalty_seconds=right_penalty_seconds,
                winner_team_name=winner_team_name,
            ),
        )
        return ("303 See Other", [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _build_parallel_sprint_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        teams = load_teams(db_path)
        active_team_names = {
            team.name for team in teams if team.category_key == category_key
        }
        sprint_entries = [
            entry
            for entry in rank_sprint_entries(load_sprint_entries(db_path, category_key))
            if entry.team_name in active_team_names
        ]
        base_minutes = _parse_hhmm(form_data.get("draw_start_time", "10:00").strip() or "10:00")
        interval_minutes = _parse_hhmm(form_data.get("draw_interval", "00:02").strip() or "00:02")
        entries = [
            SprintEntry(
                team_name=entry.team_name,
                start_order=index,
                start_time=_format_hhmm(base_minutes + (index - 1) * interval_minutes),
                base_time_seconds=0,
                buoy_penalty_seconds=0,
                behavior_penalty_seconds=0,
                status="OK",
            )
            for index, entry in enumerate(sprint_entries, start=1)
        ]
        save_parallel_sprint_start_entries(db_path, category_key, entries)
        return ("303 See Other", [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _clear_parallel_sprint_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        clear_parallel_sprint_protocol(db_path, category_key)
        return ("303 See Other", [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _clear_parallel_sprint_stage_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        stage_title = form_data.get("stage_title", "").strip()
        db_path = self.data_dir / db_name
        teams = load_teams(db_path)
        active_team_names = {
            team.name for team in teams if team.category_key == category_key
        }
        sprint_entries = [
            entry
            for entry in rank_sprint_entries(load_sprint_entries(db_path, category_key))
            if entry.team_name in active_team_names
        ]
        specs = _parallel_sprint_match_specs([entry.team_name for entry in sprint_entries])
        grouped: dict[str, list[dict[str, object]]] = {}
        order = _parallel_round_titles_in_display_order(specs)
        for spec in specs:
            grouped.setdefault(str(spec["round_title"]), []).append(spec)
        round_names = _parallel_round_names_from_title_and_later(grouped, order, stage_title)
        clear_parallel_sprint_rounds(db_path, category_key, round_names)
        return ("303 See Other", [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _save_parallel_sprint_start_list_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        row_indexes = sorted(
            {
                int(key.split("_")[1])
                for key in form_data
                if key.startswith("row_") and key.endswith("_team_name")
            }
        )
        entries: list[SprintEntry] = []
        for index in row_indexes:
            team_name = form_data.get(f"row_{index}_team_name", "").strip()
            if not team_name:
                continue
            entries.append(
                SprintEntry(
                    team_name=team_name,
                    start_order=int(form_data.get(f"row_{index}_start_order", str(index)) or index),
                    start_time=form_data.get(f"row_{index}_start_time", "").strip(),
                    base_time_seconds=0,
                    buoy_penalty_seconds=0,
                    behavior_penalty_seconds=0,
                    status="OK",
                )
            )
        save_parallel_sprint_start_entries(db_path, category_key, entries)
        return ("303 See Other", [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _save_parallel_sprint_lineup_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        lineup_target = form_data.get("lineup_target", "").strip()
        team_name, member_order, make_active = _parse_lineup_target(lineup_target)
        db_path = self.data_dir / db_name
        teams = load_teams(db_path)
        lineup_flags = load_parallel_sprint_lineup_flags(db_path, category_key)
        team = next(
            (saved_team for saved_team in teams if saved_team.category_key == category_key and saved_team.name == team_name),
            None,
        )
        if team is not None and member_order > 0:
            current_flags = _resolve_sprint_lineup(team, lineup_flags.get(team.name, {}))
            updated_flags = {
                member["member_order"]: member["is_active"]  # type: ignore[index]
                for member in current_flags
            }
            updated_flags[member_order] = make_active
            lineup_flags[team.name] = updated_flags
            save_parallel_sprint_lineup_flags(db_path, category_key, lineup_flags)
        return (
            "303 See Other",
            [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}&open_team={quote(team_name)}#parallel-lineup")],
            "",
        )

    def _save_parallel_sprint_result_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        round_name = form_data.get("round_name", "").strip()
        lane = form_data.get("lane", "").strip()
        db_path = self.data_dir / db_name
        saved_heats = {
            saved_round_name: (left, right)
            for saved_round_name, left, right in load_parallel_sprint_heats(db_path, category_key)
        }
        saved_meta = load_parallel_sprint_heat_meta(db_path, category_key)
        current = saved_heats.get(round_name)
        current_meta = saved_meta.get(round_name)
        left_existing = current[0] if current else ParallelSprintHeatResult("", "left", 0, 0, 0, "OK")
        right_existing = current[1] if current else ParallelSprintHeatResult("", "right", 0, 0, 0, "OK")
        base_time_seconds = _parse_mmss(form_data.get("base_time_seconds", "0"))
        buoy_one = int(form_data.get("buoy_one", "0") or 0)
        buoy_two = int(form_data.get("buoy_two", "0") or 0)
        penalty_seconds = buoy_one + buoy_two
        team_name = form_data.get("team_name", "").strip()
        team_start_order = int(form_data.get("team_start_order", "0") or 0)
        other_team_name = form_data.get("other_team_name", "").strip()
        other_start_order = int(form_data.get("other_start_order", "0") or 0)
        edited = ParallelSprintHeatResult(
            team_name=team_name,
            lane=lane or "left",
            start_order=team_start_order,
            total_time_seconds=base_time_seconds + penalty_seconds,
            missed_buoys=0,
            status="OK",
        )
        placeholder_total = PARALLEL_PENDING_TOTAL_SECONDS
        placeholder = ParallelSprintHeatResult(
            team_name=other_team_name,
            lane="right" if lane == "left" else "left",
            start_order=other_start_order,
            total_time_seconds=(
                right_existing.total_time_seconds
                if lane == "left" and right_existing.team_name
                else left_existing.total_time_seconds
                if lane == "right" and left_existing.team_name
                else placeholder_total
            ),
            missed_buoys=0,
            status="OK",
        )
        if lane == "left":
            left_result = edited
            right_result = right_existing if right_existing.team_name else placeholder
            left_base = base_time_seconds
            left_penalty = penalty_seconds
            right_base = (
                current_meta.right_base_time_seconds
                if current_meta and right_result.team_name
                else max(0, right_result.total_time_seconds)
                if right_result.team_name and right_result.total_time_seconds != placeholder_total
                else 0
            )
            right_penalty = current_meta.right_penalty_seconds if current_meta else 0
        else:
            right_result = edited
            left_result = left_existing if left_existing.team_name else placeholder
            right_base = base_time_seconds
            right_penalty = penalty_seconds
            left_base = (
                current_meta.left_base_time_seconds
                if current_meta and left_result.team_name
                else max(0, left_result.total_time_seconds)
                if left_result.team_name and left_result.total_time_seconds != placeholder_total
                else 0
            )
            left_penalty = current_meta.left_penalty_seconds if current_meta else 0
        winner_team_name = ""
        if left_result.team_name and right_result.team_name and placeholder_total not in {left_result.total_time_seconds, right_result.total_time_seconds}:
            winner_team_name = resolve_heat_winner(left_result, right_result).team_name
        save_parallel_sprint_heat(
            db_path=db_path,
            category_key=category_key,
            round_name=round_name,
            left=left_result,
            right=right_result,
        )
        save_parallel_sprint_heat_meta(
            db_path=db_path,
            category_key=category_key,
            meta=ParallelSprintHeatMeta(
                round_name=round_name,
                scheduled_start_time=current_meta.scheduled_start_time if current_meta else "",
                left_base_time_seconds=left_base,
                left_penalty_seconds=left_penalty,
                right_base_time_seconds=right_base,
                right_penalty_seconds=right_penalty,
                winner_team_name=winner_team_name,
            ),
        )
        spec = next((item for item in _parallel_sprint_match_specs(
            [
                team.name
                for team in [
                    team
                    for team in load_teams(db_path)
                    if team.category_key == category_key
                ]
                if team.name in {
                    entry.team_name
                    for entry in rank_sprint_entries(load_sprint_entries(db_path, category_key))
                }
            ]
        ) if str(item["round_name"]) == round_name), None)
        anchor = f"#{_parallel_round_anchor_id(str(spec['round_title']))}" if spec is not None else ""
        return (
            "303 See Other",
            [("Location", f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}&open_result={quote(round_name + '|' + lane)}{anchor}")],
            "",
        )

    def _slalom_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        category_key = query.get("category", "")
        open_team = query.get("open_team", "").strip()
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = load_teams(db_path)
        sprint_ranked = rank_sprint_entries(load_sprint_entries(db_path, category_key))
        sprint_order = {
            entry.team_name: index
            for index, entry in enumerate(sprint_ranked, start=1)
        }
        lineup_flags = load_slalom_lineup_flags(db_path, category_key)
        runs = load_slalom_runs(db_path, category_key)
        grouped: dict[str, list[object]] = {}
        grouped_for_places: dict[str, list[SlalomRun]] = {}
        for run in runs:
            grouped.setdefault(run.team_name, []).append(run)
            scored = _slalom_scored_run(run)
            if scored is not None:
                grouped_for_places.setdefault(run.team_name, []).append(scored)
        available_categories = "".join(
            (
                f"<li><strong>{escape(category.key)}</strong></li>"
                if category.key == category_key
                else f"<li><a href=\"/slalom?db={escape(db_name)}&category={escape(category.key)}\">{escape(category.key)}</a></li>"
            )
            for category in settings.categories
        ) or "<li>Категории не настроены</li>"
        category_teams = [team for team in teams if team.category_key == category_key]
        best_runs = {
            team_name: best_run_for_team(team_runs)
            for team_name, team_runs in grouped_for_places.items()
        }
        places = {
            team_name: index
            for index, (team_name, _run) in enumerate(
                sorted(best_runs.items(), key=lambda item: (item[1].total_time_seconds, item[0])),
                start=1,
            )
        }
        gate_count = max(settings.slalom_gate_count, 1)
        slalom_forms: list[str] = []
        slalom_rows: list[str] = []
        for team_index, team in enumerate(
            sorted(
                category_teams,
                key=lambda team: (
                    sprint_order.get(team.name, 9999),
                    team.start_number,
                    team.name,
                ),
            ),
            start=1,
        ):
            form_id = f"slalom-{team_index}-{team.start_number}"
            run_by_attempt = {
                run.attempt_number: run
                for run in grouped.get(team.name, [])
            }
            slalom_forms.append(
                f"""
<form id="{form_id}" method="post" action="/slalom/save">
  <input type="hidden" name="db" value="{escape(db_name)}" />
  <input type="hidden" name="category_key" value="{escape(category_key)}" />
  <input type="hidden" name="team_name" value="{escape(team.name)}" />
  <input type="hidden" name="return_anchor" value="slalom-team-{team.start_number}" />
</form>
""".strip()
            )
            slalom_rows.append(
                _slalom_team_sheet_rows_html(
                    db_name=db_name,
                    category_key=category_key,
                    form_id=form_id,
                    team=team,
                    gate_count=gate_count,
                    team_runs=grouped.get(team.name, []),
                    place=places.get(team.name),
                    is_open=team.name == open_team,
                    scored_runs=grouped_for_places.get(team.name, []),
                )
            )
        open_lineup_panel = ""
        if open_team:
            open_team_record = next(
                (team for team in category_teams if team.name == open_team),
                None,
            )
            if open_team_record is not None:
                open_lineup_panel = _slalom_lineup_panel_html(
                    db_name,
                    category_key,
                    open_team_record,
                    _resolve_sprint_lineup(
                        open_team_record,
                        lineup_flags.get(open_team_record.name, {}),
                    ),
                )
        sheet_body = (
            "".join(slalom_forms)
            + f"""
<section class="panel-card slalom-sheet-panel">
  <table class="slalom-sheet">
    <tbody>
      {"".join(slalom_rows)}
    </tbody>
  </table>
</section>
{open_lineup_panel}
"""
            if slalom_rows
            else '<div class="panel-card"><p>Для этой категории команд пока нет.</p></div>'
        )
        body = _page(
            "Слалом",
            f"""
<section class="panel-page slalom-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">Слалом</p>
      <h1>Стартовый протокол</h1>
      <p class="subtle">{escape(category_key or 'Категория не выбрана')}</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <section class="panel-card">
    <div class="section-head">
      <div>
        <h2>Категории</h2>
        <ul class="compact-list">{available_categories}</ul>
      </div>
      <div class="meta-note">
        <p class="subtle">Количество ворот: {gate_count}</p>
      </div>
    </div>
    <form method="post" action="/slalom/schedule" class="slalom-schedule-form">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="category_key" value="{escape(category_key)}" />
      <label class="slalom-schedule-field">
        <span>1-я попытка: старт</span>
        <input class="inline-time" data-time-mask="hhmmss" name="attempt_1_start_time" value="10:00:00" placeholder="10:00:00" />
      </label>
      <label class="slalom-schedule-field">
        <span>1-я попытка: интервал, мин</span>
        <input name="attempt_1_interval_minutes" value="2" inputmode="numeric" />
      </label>
      <label class="slalom-schedule-field">
        <span>2-я попытка: старт</span>
        <input class="inline-time" data-time-mask="hhmmss" name="attempt_2_start_time" value="10:30:00" placeholder="10:30:00" />
      </label>
      <label class="slalom-schedule-field">
        <span>2-я попытка: интервал, мин</span>
        <input name="attempt_2_interval_minutes" value="2" inputmode="numeric" />
      </label>
      <button type="submit" class="slalom-schedule-submit">Сформировать старты</button>
    </form>
    <form method="post" action="/slalom/clear" onsubmit="return confirm('Очистить весь слалом для этой категории?');">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="category_key" value="{escape(category_key)}" />
      <button type="submit" class="danger-button slalom-clear-button">Очистить</button>
    </form>
  </section>
  {sheet_body}
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _save_slalom_lineup_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        lineup_target = form_data.get("lineup_target", "").strip()
        team_name, member_order, make_active = _parse_lineup_target(lineup_target)
        db_path = self.data_dir / db_name
        teams = load_teams(db_path)
        lineup_flags = load_slalom_lineup_flags(db_path, category_key)
        if not team_name:
            team_name = form_data.get("team_name", "").strip()
        team = next(
            (saved_team for saved_team in teams if saved_team.category_key == category_key and saved_team.name == team_name),
            None,
        )
        if team is not None and member_order > 0:
            current_flags = _resolve_sprint_lineup(team, lineup_flags.get(team.name, {}))
            updated_flags = {
                member["member_order"]: member["is_active"]  # type: ignore[index]
                for member in current_flags
            }
            updated_flags[member_order] = make_active
            lineup_flags[team.name] = updated_flags
            save_slalom_lineup_flags(db_path, category_key, lineup_flags)
        return (
            "303 See Other",
            [("Location", f"/slalom?db={quote(db_name)}&category={quote(category_key)}&open_team={quote(team_name)}#slalom-lineup")],
            "",
        )

    def _save_slalom_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        team_name = form_data.get("team_name", "").strip()
        settings = load_competition_settings(db_path)
        for attempt_number in (1, 2):
            base_value = form_data.get(f"attempt_{attempt_number}_base_time_seconds", "").strip()
            if not base_value:
                continue
            gate_indexes = sorted(
                {
                    int(key.rsplit("_", 1)[1])
                    for key in form_data
                    if key.startswith(f"attempt_{attempt_number}_gate_")
                }
            )
            gate_count = gate_indexes[-1] if gate_indexes else max(settings.slalom_gate_count, 1)
            gate_penalties = [
                int(form_data.get(f"attempt_{attempt_number}_gate_{gate_index}", "0") or 0)
                for gate_index in range(1, gate_count + 1)
            ]
            save_slalom_run(
                db_path=db_path,
                category_key=category_key,
                team_name=team_name,
                attempt_number=attempt_number,
                base_time_seconds=_parse_hhmmss(base_value),
                finish_time_seconds=_parse_hhmmss(
                    form_data.get(f"attempt_{attempt_number}_finish_time_seconds", "").strip()
                ) if form_data.get(f"attempt_{attempt_number}_finish_time_seconds", "").strip() else 0,
                gate_penalties=gate_penalties,
            )
        anchor = form_data.get("return_anchor", "").strip()
        anchor_suffix = f"#{quote(anchor)}" if anchor else ""
        return ("303 See Other", [("Location", f"/slalom?db={quote(db_name)}&category={quote(category_key)}{anchor_suffix}")], "")

    def _clear_slalom_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        clear_slalom_category(db_path, category_key)
        return ("303 See Other", [("Location", f"/slalom?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _schedule_slalom_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = [
            team
            for team in load_teams(db_path)
            if team.category_key == category_key
        ]
        sprint_ranked = rank_sprint_entries(load_sprint_entries(db_path, category_key))
        sprint_order = {
            entry.team_name: index
            for index, entry in enumerate(sprint_ranked, start=1)
        }
        teams.sort(key=lambda team: (sprint_order.get(team.name, 9999), team.start_number, team.name))
        runs = load_slalom_runs(db_path, category_key)
        runs_by_team_attempt = {
            (run.team_name, run.attempt_number): run
            for run in runs
        }
        attempt_1_start_seconds = _parse_hhmmss(form_data.get("attempt_1_start_time", "").strip())
        attempt_1_interval_seconds = int(form_data.get("attempt_1_interval_minutes", "0") or 0) * 60
        attempt_2_start_seconds = _parse_hhmmss(form_data.get("attempt_2_start_time", "").strip())
        attempt_2_interval_seconds = int(form_data.get("attempt_2_interval_minutes", "0") or 0) * 60
        gate_count = max(settings.slalom_gate_count, 1)
        for index, team in enumerate(teams):
            attempt_1_start = attempt_1_start_seconds + index * attempt_1_interval_seconds
            attempt_2_start = attempt_2_start_seconds + index * attempt_2_interval_seconds
            existing_1 = runs_by_team_attempt.get((team.name, 1))
            existing_2 = runs_by_team_attempt.get((team.name, 2))
            save_slalom_run(
                db_path=db_path,
                category_key=category_key,
                team_name=team.name,
                attempt_number=1,
                base_time_seconds=attempt_1_start,
                gate_penalties=(existing_1.gate_penalties if existing_1 else [0] * gate_count),
                finish_time_seconds=(getattr(existing_1, "finish_time_seconds", 0) if existing_1 else 0),
            )
            save_slalom_run(
                db_path=db_path,
                category_key=category_key,
                team_name=team.name,
                attempt_number=2,
                base_time_seconds=attempt_2_start,
                gate_penalties=(existing_2.gate_penalties if existing_2 else [0] * gate_count),
                finish_time_seconds=(getattr(existing_2, "finish_time_seconds", 0) if existing_2 else 0),
            )
        return ("303 See Other", [("Location", f"/slalom?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _long_race_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        category_key = query.get("category", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        teams = load_teams(db_path)
        open_team = query.get("open_team", "").strip()
        saved_entries = load_long_race_entries(db_path, category_key)
        lineup_flags = load_long_race_lineup_flags(db_path, category_key)
        entry_by_team = {entry.team_name: entry for entry in saved_entries}
        ranked_entries = rank_sprint_entries(saved_entries)
        places_by_team = {entry.team_name: index for index, entry in enumerate(ranked_entries, start=1)}
        available_categories = "".join(
            (
                f"<li><strong>{escape(category.key)}</strong></li>"
                if category.key == category_key
                else f"<li><a href=\"/long-race?db={escape(db_name)}&category={escape(category.key)}\">{escape(category.key)}</a></li>"
            )
            for category in settings.categories
        ) or "<li>Категории не настроены</li>"
        available_teams = [team for team in teams if team.category_key == category_key]
        default_order = _long_race_start_order(db_path, category_key, available_teams)
        default_position = {
            team.name: index for index, team in enumerate(default_order, start=1)
        }
        rows = "".join(
            _long_race_table_row(
                index,
                db_name,
                category_key,
                team,
                entry_by_team.get(team.name),
                places_by_team.get(team.name),
                _resolve_sprint_lineup(team, lineup_flags.get(team.name, {})),
                open_team == team.name,
            )
            for index, team in enumerate(
                sorted(
                    available_teams,
                    key=lambda team: (
                        entry_by_team.get(team.name).start_order if entry_by_team.get(team.name) else 1,
                        default_position.get(team.name, 9999),
                        team.start_number,
                        team.name,
                    ),
                ),
                start=1,
            )
        ) or '<tr><td colspan="10">Для этой категории команд пока нет</td></tr>'
        body = _page(
            "Длинная гонка",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">Длинная гонка</p>
      <h1>Стартовый протокол</h1>
      <p class="subtle">{escape(category_key or 'Категория не выбрана')}</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <section class="panel-card">
    <form method="post" action="/long-race/save" class="stack-form">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="category_key" value="{escape(category_key)}" />
      <div class="section-head">
        <div>
          <h2>Категории</h2>
          <ul class="compact-list">{available_categories}</ul>
        </div>
        <div class="team-actions">
          <label>Время старта <input class="inline-time" data-time-mask="hhmm" name="draw_start_time" value="10:00" placeholder="10:00" /></label>
          <label>Промежуток <input class="inline-time" data-time-mask="hhmm" name="draw_interval" value="00:10" placeholder="00:10" /></label>
          <button type="submit" formaction="/long-race/build" class="inline-action">Сформировать стартовый порядок</button>
        </div>
      </div>
      <table class="protocol-table">
        <thead>
          <tr>
            <th class="col-pp">№ п/п</th>
            <th class="col-time">Время<br />старта</th>
            <th>Команда</th>
            <th class="col-number">№</th>
            <th>Состав</th>
            <th>Субъект</th>
            <th class="col-time">Время</th>
            <th class="col-time">Штраф</th>
            <th class="col-place">Место</th>
            <th class="col-status">Статус</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <button type="submit">Сохранить результаты длинной гонки</button>
    </form>
  </section>
</section>
<script>
  document.addEventListener("DOMContentLoaded", function () {{
    document.querySelectorAll(".long-race-party-select").forEach(function(select) {{
      function syncRowState() {{
        var row = select.closest("tr");
        if (!row) {{
          return;
        }}
        var nonParticipant = select.value === "99";
        row.querySelectorAll(".long-race-dependent").forEach(function(field) {{
          field.disabled = nonParticipant;
        }});
      }}
      select.addEventListener("change", syncRowState);
      syncRowState();
    }});
  }});
</script>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _save_long_race_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        row_indexes = sorted(
            {
                int(key.split("_")[1])
                for key in form_data
                if key.startswith("row_") and key.endswith("_team_name")
            }
        )
        entries: list[SprintEntry] = []
        for index in row_indexes:
            team_name = form_data.get(f"row_{index}_team_name", "").strip()
            if not team_name:
                continue
            entries.append(
                SprintEntry(
                    team_name=team_name,
                    start_order=int(form_data.get(f"row_{index}_start_order", "0") or 0),
                    start_time=form_data.get(f"row_{index}_start_time", "").strip(),
                    base_time_seconds=_parse_mmss(form_data.get(f"row_{index}_base_time_seconds", "0")),
                    buoy_penalty_seconds=0,
                    behavior_penalty_seconds=_parse_mmss(form_data.get(f"row_{index}_behavior_penalty_seconds", "0")),
                    status="Н/СТ"
                    if int(form_data.get(f"row_{index}_start_order", "0") or 0) == 99
                    else _normalize_sprint_status(form_data.get(f"row_{index}_status", "OK").strip() or "OK"),
                )
            )
        save_long_race_entries(db_path, category_key, entries)
        return ("303 See Other", [("Location", f"/long-race?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _build_long_race_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        db_path = self.data_dir / db_name
        teams = [team for team in load_teams(db_path) if team.category_key == category_key]
        saved_entries = {entry.team_name: entry for entry in load_long_race_entries(db_path, category_key)}
        row_indexes = sorted(
            {
                int(key.split("_")[1])
                for key in form_data
                if key.startswith("row_") and key.endswith("_team_name")
            }
        )
        requested_groups = {
            form_data.get(f"row_{index}_team_name", "").strip(): int(form_data.get(f"row_{index}_start_order", "1") or 1)
            for index in row_indexes
            if form_data.get(f"row_{index}_team_name", "").strip()
        }
        draw_start_time = form_data.get("draw_start_time", "10:00").strip() or "10:00"
        draw_interval = form_data.get("draw_interval", "00:10").strip() or "00:10"
        base_minutes = _parse_hhmm(draw_start_time)
        interval_minutes = _parse_hhmm(draw_interval)
        ordered_teams = _long_race_start_order(db_path, category_key, teams)
        order_position = {
            team.name: index for index, team in enumerate(ordered_teams, start=1)
        }
        order = sorted(
            ordered_teams,
            key=lambda team: (
                999 if requested_groups.get(team.name, 1) == 99 else requested_groups.get(team.name, 1),
                order_position.get(team.name, 9999),
            ),
        )
        entries: list[SprintEntry] = []
        for team in order:
            current = saved_entries.get(team.name)
            group_number = requested_groups.get(team.name, 1)
            if group_number == 99:
                group_time = ""
            else:
                group_time = _format_hhmm(base_minutes + (group_number - 1) * interval_minutes)
            entries.append(
                SprintEntry(
                    team_name=team.name,
                    start_order=group_number,
                    start_time=(group_time or (current.start_time if current else "")),
                    base_time_seconds=current.base_time_seconds if current else 0,
                    buoy_penalty_seconds=0,
                    behavior_penalty_seconds=current.behavior_penalty_seconds if current else 0,
                    status="Н/СТ" if group_number == 99 else _normalize_sprint_status(current.status if current else "OK"),
                )
            )
        save_long_race_entries(db_path, category_key, entries)
        return ("303 See Other", [("Location", f"/long-race?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _save_long_race_lineup_response(
        self,
        form_data: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = form_data.get("db", "")
        category_key = form_data.get("category_key", "")
        lineup_target = form_data.get("lineup_target", "").strip()
        team_name, member_order, make_active = _parse_lineup_target(lineup_target)
        db_path = self.data_dir / db_name
        teams = load_teams(db_path)
        lineup_flags = load_long_race_lineup_flags(db_path, category_key)
        team = next(
            (saved_team for saved_team in teams if saved_team.category_key == category_key and saved_team.name == team_name),
            None,
        )
        if team is not None and member_order > 0:
            current_flags = _resolve_sprint_lineup(team, lineup_flags.get(team.name, {}))
            updated_flags = {
                member["member_order"]: member["is_active"]  # type: ignore[index]
                for member in current_flags
            }
            updated_flags[member_order] = make_active
            lineup_flags[team.name] = updated_flags
            save_long_race_lineup_flags(db_path, category_key, lineup_flags)
        return ("303 See Other", [("Location", f"/long-race?db={quote(db_name)}&category={quote(category_key)}")], "")

    def _export_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        def _doc_row(title: str, base_url: str) -> str:
            return (
                f'<li class="export-row">'
                f'<span class="export-row-title">{title}</span>'
                f'<span class="export-row-actions">'
                f'<a href="{base_url}?db={escape(db_name)}">Просмотр</a>'
                f'<a href="{base_url}/pdf?db={escape(db_name)}">PDF</a>'
                f'<a href="{base_url}/xlsx?db={escape(db_name)}">Excel</a>'
                f'</span></li>'
            )
        document_rows = "".join(
            [
                _doc_row("Итоговый протокол спринта", "/export/sprint-results"),
                _doc_row("Итоговый протокол слалома", "/export/slalom-results"),
                _doc_row("Итоговый протокол H2H", "/export/parallel-sprint-results"),
                _doc_row("Итоговый протокол длинной гонки", "/export/long-race-results"),
                _doc_row("Протокол многоборья", "/export/combined-results"),
                '<li><span class="subtle">Судейский состав — скоро</span></li>',
                '<li><span class="subtle">Стартовый протокол длинной гонки — скоро</span></li>',
            ]
        )
        body = _page(
            "Протоколы",
            f"""
<section class="panel-page">
  <div class="page-head">
    <div>
      <p class="eyebrow">Протоколы</p>
      <h1>Протоколы</h1>
      <p class="subtle">Реестр документов соревнования для проверки, печати и дальнейшего экспорта.</p>
    </div>
    <a class="secondary-link" href="/dashboard?db={escape(db_name)}">Назад на рабочий стол</a>
  </div>
  <section class="panel-card">
    <h2>Реестр документов</h2>
    <ul class="compact-list roomy">{document_rows}</ul>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _sprint_results_protocol_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        judges = load_judges(db_path)
        teams = load_teams(db_path)
        category_sections = []
        for category in settings.categories:
            category_teams = [team for team in teams if team.category_key == category.key]
            sprint_entries = [
                SprintEntry(
                    team_name=entry.team_name,
                    start_order=entry.start_order,
                    base_time_seconds=entry.base_time_seconds,
                    buoy_penalty_seconds=entry.buoy_penalty_seconds,
                    behavior_penalty_seconds=entry.behavior_penalty_seconds,
                    status=_normalize_sprint_status(entry.status),
                    start_time=entry.start_time,
                )
                for entry in load_sprint_entries(db_path, category.key)
            ]
            if not category_teams and not sprint_entries:
                continue
            entry_by_team = {entry.team_name: entry for entry in sprint_entries}
            ranked_entries = rank_sprint_entries(sprint_entries)
            places_by_team = {
                entry.team_name: index for index, entry in enumerate(ranked_entries, start=1)
            }
            lineup_flags = load_sprint_lineup_flags(db_path, category.key)
            rows = "".join(
                _sprint_results_protocol_row(
                    team,
                    entry_by_team.get(team.name),
                    places_by_team.get(team.name),
                    _resolve_sprint_lineup(team, lineup_flags.get(team.name, {})),
                )
                for team in sorted(
                    category_teams,
                    key=lambda team: (
                        places_by_team.get(team.name, 9999),
                        entry_by_team.get(team.name).start_order if entry_by_team.get(team.name) else 9999,
                        team.start_number,
                        team.name,
                    ),
                )
            ) or '<tr><td colspan="11">Нет данных по категории</td></tr>'
            category_sections.append(
                f"""
<section class="panel-card">
  <h2>{escape(_category_label(category))}</h2>
  <table class="protocol-table protocol-table-results protocol-table-slalom-results">
    <thead>
      <tr>
        <th class="col-pp">№<br />п/п</th>
        <th class="col-number">№</th>
        <th>Команда</th>
        <th>Состав</th>
        <th>Субъект</th>
        <th class="col-time">Время старта</th>
        <th class="col-time">Время</th>
        <th class="col-time">Штраф</th>
        <th class="col-place">Место</th>
        <th class="col-place">Очки</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
            )
        competition_dates = ", ".join(settings.competition_dates or [settings.competition_date])
        body = _page(
            "Итоговый протокол спринта",
            f"""
<section class="panel-page protocol-page">
  <div class="page-head protocol-head">
    <a class="secondary-link protocol-back" href="/export?db={escape(db_name)}">Назад к протоколам</a>
    <span class="protocol-download-actions"><a class="secondary-link" href="/export/sprint-results/pdf?db={escape(db_name)}">PDF</a><a class="secondary-link" href="/export/sprint-results/xlsx?db={escape(db_name)}">Excel</a></span>
    <div class="protocol-title-block">
      <p class="eyebrow">{escape(settings.organizer or 'Организатор не указан')}</p>
      <h1>Итоговый протокол</h1>
      <p class="subtle">Дисциплина: Спринт</p>
    </div>
  </div>
  <section class="panel-card protocol-summary">
    <dl class="summary-grid">
      <div><dt>Соревнование</dt><dd>{escape(settings.name or 'Не указано')}</dd></div>
      <div><dt>Даты</dt><dd>{escape(competition_dates or 'Не указаны')}</dd></div>
      <div><dt>Место проведения</dt><dd>{escape(settings.venue or 'Не указано')}</dd></div>
      <div><dt>Организатор</dt><dd>{escape(settings.organizer or 'Не указан')}</dd></div>
    </dl>
  </section>
  {''.join(category_sections) or '<section class="panel-card"><p>По спринту пока нет данных.</p></section>'}
  <section class="panel-card protocol-footer">
    <div class="protocol-signatures">
      <div class="protocol-signature">
        <dt>Главный судья</dt>
        <dd>{escape(_judge_full_name(judges.chief_judge) or 'Не заполнено')}</dd>
      </div>
      <div class="protocol-signature">
        <dt>Главный секретарь</dt>
        <dd>{escape(_judge_full_name(judges.chief_secretary) or 'Не заполнено')}</dd>
      </div>
    </div>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _combined_results_protocol_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        judges = load_judges(db_path)
        teams = load_teams(db_path)
        category_sections = []
        for category in settings.categories:
            category_teams = [team for team in teams if team.category_key == category.key]
            if not category_teams:
                continue
            sprint_ranked = rank_sprint_entries(
                [
                    SprintEntry(
                        team_name=entry.team_name,
                        start_order=entry.start_order,
                        base_time_seconds=entry.base_time_seconds,
                        buoy_penalty_seconds=entry.buoy_penalty_seconds,
                        behavior_penalty_seconds=entry.behavior_penalty_seconds,
                        status=_normalize_sprint_status(entry.status),
                        start_time=entry.start_time,
                    )
                    for entry in load_sprint_entries(db_path, category.key)
                ]
            )
            sprint_places = _place_map_from_ranked_entries(sprint_ranked)
            sprint_points = _points_from_ranked_entries("sprint", sprint_ranked)

            long_race_ranked = rank_sprint_entries(
                [
                    SprintEntry(
                        team_name=entry.team_name,
                        start_order=entry.start_order,
                        base_time_seconds=entry.base_time_seconds,
                        buoy_penalty_seconds=entry.buoy_penalty_seconds,
                        behavior_penalty_seconds=entry.behavior_penalty_seconds,
                        status=_normalize_sprint_status(entry.status),
                        start_time=entry.start_time,
                    )
                    for entry in load_long_race_entries(db_path, category.key)
                ]
            )
            long_race_places = _place_map_from_ranked_entries(long_race_ranked)
            long_race_points = _long_race_points_from_ranked_entries(long_race_ranked)

            slalom_runs = load_slalom_runs(db_path, category.key)
            slalom_places = _slalom_places_map(slalom_runs)
            slalom_points = _slalom_points_map(slalom_runs)

            parallel_heats = load_parallel_sprint_heats(db_path, category.key)
            parallel_saved_by_round = {
                round_name: (left, right)
                for round_name, left, right in parallel_heats
            }
            parallel_places = _parallel_sprint_full_places_map(category_teams, parallel_saved_by_round)
            parallel_points = {
                team_name: points_for_place("parallel_sprint", place)
                for team_name, place in parallel_places.items()
            }

            combined_rows = combine_points(
                sprint_points=sprint_points,
                parallel_sprint_points=parallel_points,
                slalom_points=slalom_points,
                long_race_points=long_race_points,
            )
            combined_places = {
                team_name: index for index, (team_name, _points) in enumerate(combined_rows, start=1)
            }
            combined_points = {team_name: points for team_name, points in combined_rows}
            rows = "".join(
                _combined_results_protocol_row(
                    team,
                    sprint_places.get(team.name),
                    sprint_points.get(team.name, 0),
                    parallel_places.get(team.name),
                    parallel_points.get(team.name, 0),
                    slalom_places.get(team.name),
                    slalom_points.get(team.name, 0),
                    long_race_places.get(team.name),
                    long_race_points.get(team.name, 0),
                    combined_places.get(team.name),
                    combined_points.get(team.name, 0),
                )
                for team in sorted(
                    category_teams,
                    key=lambda team: (
                        combined_places.get(team.name, 9999),
                        team.start_number,
                        team.name,
                    ),
                )
            ) or '<tr><td colspan="9">Нет данных по категории</td></tr>'
            category_sections.append(
                f"""
<section class="panel-card">
  <h2>{escape(_category_label(category))}</h2>
  <table class="protocol-table protocol-table-combined">
    <thead>
      <tr>
        <th class="col-number">№</th>
        <th>Команда</th>
        <th>Состав</th>
        <th>Субъект</th>
        <th class="col-discipline">Спринт</th>
        <th class="col-discipline">H2H</th>
        <th class="col-discipline">Слалом</th>
        <th class="col-discipline">Длинная гонка</th>
        <th class="col-discipline" title="Многоборье">Много-<br />борье</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
            )
        competition_dates = ", ".join(settings.competition_dates or [settings.competition_date])
        body = _page(
            "Протокол многоборья",
            f"""
<section class="panel-page protocol-page">
  <div class="page-head protocol-head">
    <a class="secondary-link protocol-back" href="/export?db={escape(db_name)}">Назад к протоколам</a>
    <span class="protocol-download-actions"><a class="secondary-link" href="/export/combined-results/pdf?db={escape(db_name)}">PDF</a><a class="secondary-link" href="/export/combined-results/xlsx?db={escape(db_name)}">Excel</a></span>
    <div class="protocol-title-block">
      <p class="eyebrow">{escape(settings.organizer or 'Организатор не указан')}</p>
      <h1>Протокол многоборья</h1>
      <p class="subtle">Итоговый зачет по дисциплинам</p>
    </div>
  </div>
  <section class="panel-card protocol-summary">
    <dl class="summary-grid">
      <div><dt>Соревнование</dt><dd>{escape(settings.name or 'Не указано')}</dd></div>
      <div><dt>Даты</dt><dd>{escape(competition_dates or 'Не указаны')}</dd></div>
      <div><dt>Место проведения</dt><dd>{escape(settings.venue or 'Не указано')}</dd></div>
      <div><dt>Организатор</dt><dd>{escape(settings.organizer or 'Не указан')}</dd></div>
    </dl>
  </section>
  {''.join(category_sections) or '<section class="panel-card"><p>По многоборью пока нет данных.</p></section>'}
  <section class="panel-card protocol-footer">
    <div class="protocol-signatures">
      <div class="protocol-signature">
        <dt>Главный судья</dt>
        <dd>{escape(_judge_full_name(judges.chief_judge) or 'Не заполнено')}</dd>
      </div>
      <div class="protocol-signature">
        <dt>Главный секретарь</dt>
        <dd>{escape(_judge_full_name(judges.chief_secretary) or 'Не заполнено')}</dd>
      </div>
    </div>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _slalom_results_protocol_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        judges = load_judges(db_path)
        teams = load_teams(db_path)
        category_sections = []
        for category in settings.categories:
            category_teams = [team for team in teams if team.category_key == category.key]
            slalom_runs = load_slalom_runs(db_path, category.key)
            if not category_teams and not slalom_runs:
                continue
            slalom_places = _slalom_places_map(slalom_runs)
            grouped_runs: dict[str, list[object]] = {}
            scored_by_team: dict[str, list[SlalomRun]] = {}
            for run in slalom_runs:
                grouped_runs.setdefault(run.team_name, []).append(run)
                scored = _slalom_scored_run(run)
                if scored is not None:
                    scored_by_team.setdefault(run.team_name, []).append(scored)
            lineup_flags = load_slalom_lineup_flags(db_path, category.key)
            column_count = 8 + settings.slalom_gate_count
            rows = "".join(
                _slalom_results_protocol_row(
                    team,
                    grouped_runs.get(team.name, []),
                    slalom_places.get(team.name),
                    _resolve_sprint_lineup(team, lineup_flags.get(team.name, {})),
                    scored_by_team.get(team.name, []),
                    settings.slalom_gate_count,
                )
                for team in sorted(
                    category_teams,
                    key=lambda team: (
                        slalom_places.get(team.name, 9999),
                        team.start_number,
                        team.name,
                    ),
                )
            ) or f'<tr><td colspan="{column_count}">Нет данных по категории</td></tr>'
            gate_headers = "".join(
                f'<th class="slalom-gate-col">{gate_index}в</th>'
                for gate_index in range(1, settings.slalom_gate_count + 1)
            )
            gate_colgroups = "".join('<col class="slalom-gate-colgroup" />' for _ in range(settings.slalom_gate_count))
            category_sections.append(
                f"""
<section class="panel-card">
  <h2>{escape(_category_label(category))}</h2>
  <table class="protocol-table protocol-table-slalom-sheet">
    <colgroup>
      <col class="slalom-col-number" />
      <col class="slalom-col-team" />
      <col class="slalom-col-subject" />
      <col class="slalom-col-crew" />
      <col class="slalom-col-attempt" />
      <col class="slalom-col-start" />
      <col class="slalom-col-finish" />
      {gate_colgroups}
      <col class="slalom-col-total" />
      <col class="slalom-col-place" />
    </colgroup>
    <thead>
      <tr>
        <th class="col-number">№</th>
        <th>Команда</th>
        <th>Субъект</th>
        <th>Состав команды</th>
        <th class="slalom-attempt-col">Попытка</th>
        <th class="col-time">старт</th>
        <th class="col-time">финиш</th>
        {gate_headers}
        <th class="col-time">итог</th>
        <th class="col-place">Место</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
            )
        competition_dates = ", ".join(settings.competition_dates or [settings.competition_date])
        body = _page(
            "Итоговый протокол слалома",
            f"""
<section class="panel-page protocol-page">
  <div class="page-head protocol-head">
    <a class="secondary-link protocol-back" href="/export?db={escape(db_name)}">Назад к протоколам</a>
    <span class="protocol-download-actions"><a class="secondary-link" href="/export/slalom-results/pdf?db={escape(db_name)}">PDF</a><a class="secondary-link" href="/export/slalom-results/xlsx?db={escape(db_name)}">Excel</a></span>
    <div class="protocol-title-block">
      <p class="eyebrow">{escape(settings.organizer or 'Организатор не указан')}</p>
      <h1>Итоговый протокол</h1>
      <p class="subtle">Дисциплина: Слалом</p>
    </div>
  </div>
  <section class="panel-card protocol-summary">
    <dl class="summary-grid">
      <div><dt>Соревнование</dt><dd>{escape(settings.name or 'Не указано')}</dd></div>
      <div><dt>Даты</dt><dd>{escape(competition_dates or 'Не указаны')}</dd></div>
      <div><dt>Место проведения</dt><dd>{escape(settings.venue or 'Не указано')}</dd></div>
      <div><dt>Организатор</dt><dd>{escape(settings.organizer or 'Не указан')}</dd></div>
    </dl>
  </section>
  {''.join(category_sections) or '<section class="panel-card"><p>По слалому пока нет данных.</p></section>'}
  <section class="panel-card protocol-footer">
    <div class="protocol-signatures">
      <div class="protocol-signature">
        <dt>Главный судья</dt>
        <dd>{escape(_judge_full_name(judges.chief_judge) or 'Не заполнено')}</dd>
      </div>
      <div class="protocol-signature">
        <dt>Главный секретарь</dt>
        <dd>{escape(_judge_full_name(judges.chief_secretary) or 'Не заполнено')}</dd>
      </div>
    </div>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _parallel_sprint_results_protocol_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        judges = load_judges(db_path)
        teams = load_teams(db_path)
        category_sections = []
        for category in settings.categories:
            category_teams = [team for team in teams if team.category_key == category.key]
            heats = load_parallel_sprint_heats(db_path, category.key)
            if not category_teams and not heats:
                continue
            saved_by_round = {
                round_name: (left, right)
                for round_name, left, right in heats
            }
            heat_meta = load_parallel_sprint_heat_meta(db_path, category.key)
            lineup_flags = load_parallel_sprint_lineup_flags(db_path, category.key)
            ordered_names = _parallel_sprint_ordered_names(category_teams, saved_by_round)
            result_by_team = _parallel_sprint_last_result_data(saved_by_round, heat_meta)
            place_map = {
                team_name: index
                for index, team_name in enumerate(ordered_names, start=1)
            }
            team_map = {team.name: team for team in category_teams}
            rows = "".join(
                _parallel_sprint_results_protocol_row(
                    team_map[team_name],
                    result_by_team.get(team_name),
                    place_map.get(team_name),
                    _resolve_sprint_lineup(team_map[team_name], lineup_flags.get(team_name, {})),
                )
                for team_name in ordered_names
                if team_name in team_map
            ) or '<tr><td colspan="9">Нет данных по категории</td></tr>'
            category_sections.append(
                f"""
<section class="panel-card">
  <h2>{escape(_category_label(category))}</h2>
  <table class="protocol-table protocol-table-results">
    <thead>
      <tr>
        <th class="col-number">№</th>
        <th>Команда</th>
        <th>Состав</th>
        <th>Субъект</th>
        <th class="col-time">Время</th>
        <th class="col-time">Штраф</th>
        <th class="col-time">Итог</th>
        <th class="col-place">Место</th>
        <th class="col-place">Очки</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
            )
        competition_dates = ", ".join(settings.competition_dates or [settings.competition_date])
        body = _page(
            "Итоговый протокол H2H",
            f"""
<section class="panel-page protocol-page">
  <div class="page-head protocol-head">
    <a class="secondary-link protocol-back" href="/export?db={escape(db_name)}">Назад к протоколам</a>
    <span class="protocol-download-actions"><a class="secondary-link" href="/export/parallel-sprint-results/pdf?db={escape(db_name)}">PDF</a><a class="secondary-link" href="/export/parallel-sprint-results/xlsx?db={escape(db_name)}">Excel</a></span>
    <div class="protocol-title-block">
      <p class="eyebrow">{escape(settings.organizer or 'Организатор не указан')}</p>
      <h1>Итоговый протокол</h1>
      <p class="subtle">Дисциплина: H2H</p>
    </div>
  </div>
  <section class="panel-card protocol-summary">
    <dl class="summary-grid">
      <div><dt>Соревнование</dt><dd>{escape(settings.name or 'Не указано')}</dd></div>
      <div><dt>Даты</dt><dd>{escape(competition_dates or 'Не указаны')}</dd></div>
      <div><dt>Место проведения</dt><dd>{escape(settings.venue or 'Не указано')}</dd></div>
      <div><dt>Организатор</dt><dd>{escape(settings.organizer or 'Не указан')}</dd></div>
    </dl>
  </section>
  {''.join(category_sections) or '<section class="panel-card"><p>По H2H пока нет данных.</p></section>'}
  <section class="panel-card protocol-footer">
    <div class="protocol-signatures">
      <div class="protocol-signature">
        <dt>Главный судья</dt>
        <dd>{escape(_judge_full_name(judges.chief_judge) or 'Не заполнено')}</dd>
      </div>
      <div class="protocol-signature">
        <dt>Главный секретарь</dt>
        <dd>{escape(_judge_full_name(judges.chief_secretary) or 'Не заполнено')}</dd>
      </div>
    </div>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    def _long_race_results_protocol_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        db_path = self.data_dir / db_name
        settings = load_competition_settings(db_path)
        judges = load_judges(db_path)
        teams = load_teams(db_path)
        category_sections = []
        for category in settings.categories:
            category_teams = [team for team in teams if team.category_key == category.key]
            long_race_entries = [
                SprintEntry(
                    team_name=entry.team_name,
                    start_order=entry.start_order,
                    base_time_seconds=entry.base_time_seconds,
                    buoy_penalty_seconds=entry.buoy_penalty_seconds,
                    behavior_penalty_seconds=entry.behavior_penalty_seconds,
                    status=_normalize_sprint_status(entry.status),
                    start_time=entry.start_time,
                )
                for entry in load_long_race_entries(db_path, category.key)
            ]
            if not category_teams and not long_race_entries:
                continue
            entry_by_team = {entry.team_name: entry for entry in long_race_entries}
            ranked_entries = rank_sprint_entries(long_race_entries)
            places_by_team = {
                entry.team_name: index for index, entry in enumerate(ranked_entries, start=1)
            }
            lineup_flags = load_long_race_lineup_flags(db_path, category.key)
            rows = "".join(
                _long_race_results_protocol_row(
                    team,
                    entry_by_team.get(team.name),
                    places_by_team.get(team.name),
                    _resolve_sprint_lineup(team, lineup_flags.get(team.name, {})),
                )
                for team in sorted(
                    category_teams,
                    key=lambda team: (
                        places_by_team.get(team.name, 9999),
                        999 if (entry_by_team.get(team.name) and entry_by_team.get(team.name).start_order == 99) else (entry_by_team.get(team.name).start_order if entry_by_team.get(team.name) else 9999),
                        team.start_number,
                        team.name,
                    ),
                )
            ) or '<tr><td colspan="10">Нет данных по категории</td></tr>'
            category_sections.append(
                f"""
<section class="panel-card">
  <h2>{escape(_category_label(category))}</h2>
  <table class="protocol-table protocol-table-results">
    <thead>
      <tr>
        <th class="col-pp">№<br />п/п</th>
        <th class="col-number">№</th>
        <th>Команда</th>
        <th>Состав</th>
        <th>Субъект</th>
        <th class="col-time">Время старта</th>
        <th class="col-time">Время</th>
        <th class="col-time">Штраф</th>
        <th class="col-place">Место</th>
        <th class="col-place">Очки</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
            )
        competition_dates = ", ".join(settings.competition_dates or [settings.competition_date])
        body = _page(
            "Итоговый протокол длинной гонки",
            f"""
<section class="panel-page protocol-page">
  <div class="page-head protocol-head">
    <a class="secondary-link protocol-back" href="/export?db={escape(db_name)}">Назад к протоколам</a>
    <span class="protocol-download-actions"><a class="secondary-link" href="/export/long-race-results/pdf?db={escape(db_name)}">PDF</a><a class="secondary-link" href="/export/long-race-results/xlsx?db={escape(db_name)}">Excel</a></span>
    <div class="protocol-title-block">
      <p class="eyebrow">{escape(settings.organizer or 'Организатор не указан')}</p>
      <h1>Итоговый протокол</h1>
      <p class="subtle">Дисциплина: Длинная гонка</p>
    </div>
  </div>
  <section class="panel-card protocol-summary">
    <dl class="summary-grid">
      <div><dt>Соревнование</dt><dd>{escape(settings.name or 'Не указано')}</dd></div>
      <div><dt>Даты</dt><dd>{escape(competition_dates or 'Не указаны')}</dd></div>
      <div><dt>Место проведения</dt><dd>{escape(settings.venue or 'Не указано')}</dd></div>
      <div><dt>Организатор</dt><dd>{escape(settings.organizer or 'Не указан')}</dd></div>
    </dl>
  </section>
  {''.join(category_sections) or '<section class="panel-card"><p>По длинной гонке пока нет данных.</p></section>'}
  <section class="panel-card protocol-footer">
    <div class="protocol-signatures">
      <div class="protocol-signature">
        <dt>Главный судья</dt>
        <dd>{escape(_judge_full_name(judges.chief_judge) or 'Не заполнено')}</dd>
      </div>
      <div class="protocol-signature">
        <dt>Главный секретарь</dt>
        <dd>{escape(_judge_full_name(judges.chief_secretary) or 'Не заполнено')}</dd>
      </div>
    </div>
  </section>
</section>
""",
        )
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)

    # ── Export download routes ──────────────────────────────────────────────

    @staticmethod
    def _safe_filename(db_name: str, prefix: str, ext: str) -> str:
        import re as _re
        base = _re.sub(r"[^A-Za-z0-9_-]", "_", db_name.replace(".db", ""))
        return f"{prefix}_{base}.{ext}" if base else f"{prefix}_protocol.{ext}"

    def _sprint_results_pdf_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.sprint_export import build_sprint_pdf
        db_name = query.get("db", "")
        data = build_sprint_pdf(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "sprint", "pdf")
        return ("200 OK", [("Content-Type", "application/pdf"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _sprint_results_xlsx_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.sprint_export import build_sprint_xlsx
        db_name = query.get("db", "")
        data = build_sprint_xlsx(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "sprint", "xlsx")
        return ("200 OK", [("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _slalom_results_pdf_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.slalom_export import build_slalom_pdf
        db_name = query.get("db", "")
        data = build_slalom_pdf(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "slalom", "pdf")
        return ("200 OK", [("Content-Type", "application/pdf"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _slalom_results_xlsx_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.slalom_export import build_slalom_xlsx
        db_name = query.get("db", "")
        data = build_slalom_xlsx(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "slalom", "xlsx")
        return ("200 OK", [("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _parallel_sprint_results_pdf_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.parallel_sprint_export import build_parallel_sprint_pdf
        db_name = query.get("db", "")
        data = build_parallel_sprint_pdf(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "h2h", "pdf")
        return ("200 OK", [("Content-Type", "application/pdf"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _parallel_sprint_results_xlsx_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.parallel_sprint_export import build_parallel_sprint_xlsx
        db_name = query.get("db", "")
        data = build_parallel_sprint_xlsx(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "h2h", "xlsx")
        return ("200 OK", [("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _long_race_results_pdf_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.long_race_export import build_long_race_pdf
        db_name = query.get("db", "")
        data = build_long_race_pdf(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "long_race", "pdf")
        return ("200 OK", [("Content-Type", "application/pdf"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _long_race_results_xlsx_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.long_race_export import build_long_race_xlsx
        db_name = query.get("db", "")
        data = build_long_race_xlsx(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "long_race", "xlsx")
        return ("200 OK", [("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _combined_results_pdf_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.combined_export import build_combined_pdf
        db_name = query.get("db", "")
        data = build_combined_pdf(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "combined", "pdf")
        return ("200 OK", [("Content-Type", "application/pdf"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    def _combined_results_xlsx_response(self, query: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
        from raftsecretary.export.combined_export import build_combined_xlsx
        db_name = query.get("db", "")
        data = build_combined_xlsx(self.data_dir / db_name)
        fn = self._safe_filename(db_name, "combined", "xlsx")
        return ("200 OK", [("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Disposition", f'attachment; filename="{fn}"')], data)

    # ── End export download routes ──────────────────────────────────────────

    def _combined_response(
        self,
        query: dict[str, str],
    ) -> tuple[str, list[tuple[str, str]], str]:
        db_name = query.get("db", "")
        category_key = query.get("category", "")
        db_path = self.data_dir / db_name

        sprint_points = _points_from_ranked_entries(
            "sprint",
            rank_sprint_entries(load_sprint_entries(db_path, category_key)),
        )
        long_race_points = _long_race_points_from_ranked_entries(
            rank_sprint_entries(load_long_race_entries(db_path, category_key))
        )
        slalom_points = _slalom_points_map(load_slalom_runs(db_path, category_key))
        parallel_sprint_points = _parallel_sprint_points_map(
            load_parallel_sprint_heats(db_path, category_key)
        )

        combined_rows = combine_points(
            sprint_points=sprint_points,
            parallel_sprint_points=parallel_sprint_points,
            slalom_points=slalom_points,
            long_race_points=long_race_points,
        )
        rows = "".join(
            f"<li>{index}. {escape(team_name)} - {points}</li>"
            for index, (team_name, points) in enumerate(combined_rows, start=1)
        ) or "<li>Многоборье пока не рассчитано</li>"
        body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Многоборье</title>
  </head>
  <body>
    <h1>Многоборье</h1>
    <ol>{rows}</ol>
  </body>
</html>
"""
        return ("200 OK", [("Content-Type", "text/html; charset=utf-8")], body)


def _points_from_ranked_entries(
    discipline: str,
    entries: list[SprintEntry],
) -> dict[str, int]:
    return {
        entry.team_name: points_for_place(discipline, index)
        for index, entry in enumerate(entries, start=1)
    }


def _long_race_points_from_ranked_entries(entries: list[SprintEntry]) -> dict[str, int]:
    return {
        entry.team_name: _long_race_points_for_entry(entry, index)
        for index, entry in enumerate(entries, start=1)
    }


def _place_map_from_ranked_entries(entries: list[SprintEntry]) -> dict[str, int]:
    return {
        entry.team_name: index
        for index, entry in enumerate(entries, start=1)
    }


def _slalom_points_map(runs) -> dict[str, int]:  # type: ignore[no-untyped-def]
    grouped: dict[str, list[SlalomRun]] = {}
    for run in runs:
        scored = _slalom_scored_run(run)
        if scored is None:
            continue
        grouped.setdefault(run.team_name, []).append(scored)
    ranked = sorted(
        ((team_name, best_run_for_team(team_runs)) for team_name, team_runs in grouped.items()),
        key=lambda item: (item[1].total_time_seconds, item[0]),
    )
    return {
        team_name: points_for_place("slalom", index)
        for index, (team_name, _) in enumerate(ranked, start=1)
    }


def _slalom_places_map(runs) -> dict[str, int]:  # type: ignore[no-untyped-def]
    grouped: dict[str, list[SlalomRun]] = {}
    for run in runs:
        scored = _slalom_scored_run(run)
        if scored is None:
            continue
        grouped.setdefault(run.team_name, []).append(scored)
    ranked = sorted(
        ((team_name, best_run_for_team(team_runs)) for team_name, team_runs in grouped.items()),
        key=lambda item: (item[1].total_time_seconds, item[0]),
    )
    return {
        team_name: index
        for index, (team_name, _) in enumerate(ranked, start=1)
    }


def _slalom_scored_run(run: object) -> SlalomRun | None:
    base_time_seconds = getattr(run, "base_time_seconds", 0)
    finish_time_seconds = getattr(run, "finish_time_seconds", 0)
    if finish_time_seconds > 0:
        return SlalomRun(
            team_name=getattr(run, "team_name", ""),
            attempt_number=getattr(run, "attempt_number", 0),
            base_time_seconds=base_time_seconds,
            gate_penalties=getattr(run, "gate_penalties", []),
            finish_time_seconds=finish_time_seconds,
        )
    if 0 < base_time_seconds < 3600:
        return SlalomRun(
            team_name=getattr(run, "team_name", ""),
            attempt_number=getattr(run, "attempt_number", 0),
            base_time_seconds=0,
            gate_penalties=getattr(run, "gate_penalties", []),
            finish_time_seconds=base_time_seconds,
        )
    return None


def _parallel_sprint_points_map(heats) -> dict[str, int]:  # type: ignore[no-untyped-def]
    places = _parallel_sprint_places_map(heats)
    if not places:
        return {}
    return {
        team_name: points_for_place("parallel_sprint", place)
        for team_name, place in places.items()
    }


def _parallel_sprint_places_map(heats) -> dict[str, int]:  # type: ignore[no-untyped-def]
    final_a = next((heat for heat in heats if heat[0] == "final_a"), None)
    if not final_a:
        return {}
    _round_name, final_a_left, final_a_right = final_a
    final_b = next((heat for heat in heats if heat[0] == "final_b"), None)
    if final_b:
        _final_b_name, final_b_left, final_b_right = final_b
        return resolve_four_team_places(
            (final_a_left, final_a_right),
            (final_b_left, final_b_right),
        )
    winner = final_a_left if final_a_left.total_time_seconds <= final_a_right.total_time_seconds else final_a_right
    loser = final_a_right if winner is final_a_left else final_a_left
    return {
        winner.team_name: 1,
        loser.team_name: 2,
    }


def _parallel_sprint_round_title(bracket_size: int) -> str:
    return {
        2: "Финал A",
        4: "1/2 финала",
        8: "1/4 финала",
        16: "1/8 финала",
        32: "1/16 финала",
    }.get(bracket_size, f"Раунд на {bracket_size} команд")


def _parallel_sprint_rounds(
    initial_pairs: list[tuple[str, str]],
    second_stage_size: int,
) -> list[tuple[str, list[tuple[str, str]]]]:
    if not initial_pairs or second_stage_size < 2:
        return []
    if second_stage_size == 2:
        return [("Финал A", initial_pairs)]

    rounds: list[tuple[str, list[tuple[str, str]]]] = []
    current_matches = initial_pairs
    current_size = second_stage_size
    heat_prefix = "второго этапа"
    while current_size > 2:
        rounds.append((_parallel_sprint_round_title(current_size), current_matches))
        if len(current_matches) == 2:
            rounds.append((
                "Финал B",
                [("Проигравший полуфинала 1", "Проигравший полуфинала 2")],
            ))
            rounds.append((
                "Финал A",
                [("Победитель полуфинала 1", "Победитель полуфинала 2")],
            ))
            break
        next_matches = []
        for index in range(0, len(current_matches), 2):
            left_heat = index + 1
            right_heat = index + 2
            next_matches.append(
                (
                    f"Победитель заезда {left_heat} {heat_prefix}",
                    f"Победитель заезда {right_heat} {heat_prefix}",
                )
            )
        current_matches = next_matches
        current_size //= 2
    return rounds


def _parallel_sprint_match_specs(seeded_teams: list[str]) -> list[dict[str, object]]:
    if len(seeded_teams) < 3:
        return []
    specs: list[dict[str, object]] = []
    for index, (target_seed, left, right) in enumerate(build_stage_one_matches(seeded_teams), start=1):
        specs.append(
            {
                "round_name": f"stage1_seed_{target_seed}",
                "round_title": "Первый этап",
                "match_index": index,
                "left_source": ("team", (left, seeded_teams.index(left) + 1)),
                "right_source": ("team", (right, seeded_teams.index(right) + 1)),
            }
        )

    bracket_size = main_bracket_size(len(seeded_teams))
    direct_qualifiers, _ = split_direct_qualifiers_and_stage_one(seeded_teams)
    entrants: dict[int, tuple[str, object]] = {
        seed: ("team", (team_name, seed)) for seed, team_name in enumerate(direct_qualifiers, start=1)
    }
    for target_seed, _left, _right in build_stage_one_matches(seeded_teams):
        entrants[target_seed] = ("winner", f"stage1_seed_{target_seed}")

    seed_order = second_stage_seed_order(bracket_size)
    current_matches: list[dict[str, object]] = []
    stage_size = bracket_size
    round_names = {
        2: "final_a",
        4: "semifinal",
        8: "quarterfinal",
        16: "eighthfinal",
        32: "sixteenthfinal",
    }
    for index, (left_seed, right_seed) in enumerate(zip(seed_order[::2], seed_order[1::2], strict=True), start=1):
        current_matches.append(
            {
                "round_name": f"{round_names.get(stage_size, 'round')}_{index}",
                "round_title": _parallel_sprint_round_title(stage_size),
                "match_index": index,
                "left_source": entrants[left_seed],
                "right_source": entrants[right_seed],
            }
        )
    specs.extend(current_matches)

    while stage_size > 4:
        next_matches: list[dict[str, object]] = []
        stage_size //= 2
        for index in range(0, len(current_matches), 2):
            left_match = current_matches[index]
            right_match = current_matches[index + 1]
            next_matches.append(
                {
                    "round_name": f"{round_names.get(stage_size, 'round')}_{len(next_matches)+1}",
                    "round_title": _parallel_sprint_round_title(stage_size),
                    "match_index": len(next_matches) + 1,
                    "left_source": ("winner", str(left_match["round_name"])),
                    "right_source": ("winner", str(right_match["round_name"])),
                }
            )
        specs.extend(next_matches)
        current_matches = next_matches

    if stage_size == 4 and len(current_matches) == 2:
        specs.append(
            {
                "round_name": "final_b",
                "round_title": "Финал B",
                "match_index": 1,
                "left_source": ("loser", str(current_matches[0]["round_name"])),
                "right_source": ("loser", str(current_matches[1]["round_name"])),
            }
        )
        specs.append(
            {
                "round_name": "final_a",
                "round_title": "Финал A",
                "match_index": 1,
                "left_source": ("winner", str(current_matches[0]["round_name"])),
                "right_source": ("winner", str(current_matches[1]["round_name"])),
            }
        )
    return specs


def _parallel_sprint_columns_html(
    db_name: str,
    category_key: str,
    specs: list[dict[str, object]],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    team_map: dict[str, Team],
    start_entries_by_team: dict[str, SprintEntry],
) -> str:
    if not specs:
        return ""
    rounds: dict[str, list[dict[str, object]]] = {}
    order: list[str] = []
    for spec in specs:
        round_title = str(spec["round_title"])
        if round_title not in rounds:
            rounds[round_title] = []
            order.append(round_title)
        rounds[round_title].append(spec)
    columns = []
    for column_index, round_title in enumerate(order):
        cards = "".join(
            _parallel_sprint_heat_card_html(
                db_name,
                category_key,
                spec,
                heat_meta,
                saved_by_round,
                team_map,
                start_entries_by_team,
                show_start_time=column_index == 0,
            )
            for spec in rounds[round_title]
        )
        columns.append(
            f"""
<section class="h2h-column">
  <h2>{escape(round_title)}</h2>
  <div class="h2h-column-body">{cards}</div>
</section>
"""
        )
    return "".join(columns)


def _parallel_sprint_heat_card_html(
    db_name: str,
    category_key: str,
    spec: dict[str, object],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    team_map: dict[str, Team],
    start_entries_by_team: dict[str, SprintEntry],
    show_start_time: bool,
) -> str:
    round_name = str(spec["round_name"])
    participants = _parallel_resolved_heat_participants(spec, heat_meta, saved_by_round)
    meta = heat_meta.get(round_name)
    left_name = participants["left_name"]
    right_name = participants["right_name"]
    left_seed = participants["left_seed"]
    right_seed = participants["right_seed"]
    can_edit = participants["left_is_actual"] and participants["right_is_actual"]
    winner_name = meta.winner_team_name if meta and meta.winner_team_name in {left_name, right_name} else ""
    left_is_winner = bool(winner_name and winner_name == left_name)
    right_is_winner = bool(winner_name and winner_name == right_name)
    buoy_pattern = _parallel_buoy_pattern(
        meta.left_penalty_seconds if meta else 0,
        meta.right_penalty_seconds if meta else 0,
    )
    left_row = _parallel_competitor_row_html(
        side="left",
        team_name=left_name,
        start_order=left_seed,
        team=team_map.get(left_name),
        base_time_seconds=meta.left_base_time_seconds if meta else 0,
        penalty_seconds=meta.left_penalty_seconds if meta else 0,
        status_value=saved_by_round[round_name][0].status if round_name in saved_by_round else "OK",
        is_resolved=participants["left_is_actual"],
        is_winner=left_is_winner,
        is_loser=bool(winner_name) and not left_is_winner,
        scheduled_start_time=meta.scheduled_start_time if meta else "",
        start_entry=start_entries_by_team.get(left_name),
        db_name=db_name,
        category_key=category_key,
        show_start_time=show_start_time,
    )
    right_row = _parallel_competitor_row_html(
        side="right",
        team_name=right_name,
        start_order=right_seed,
        team=team_map.get(right_name),
        base_time_seconds=meta.right_base_time_seconds if meta else 0,
        penalty_seconds=meta.right_penalty_seconds if meta else 0,
        status_value=saved_by_round[round_name][1].status if round_name in saved_by_round else "OK",
        is_resolved=participants["right_is_actual"],
        is_winner=right_is_winner,
        is_loser=bool(winner_name) and not right_is_winner,
        scheduled_start_time=meta.scheduled_start_time if meta else "",
        start_entry=start_entries_by_team.get(right_name),
        db_name=db_name,
        category_key=category_key,
        show_start_time=show_start_time,
    )
    disabled_form = "" if can_edit else ' disabled="disabled"'
    winner_text = winner_name if winner_name else "Ожидание результата"
    return f"""
<form method="post" action="/parallel-sprint/save" class="h2h-heat-card">
  <input type="hidden" name="db" value="{escape(db_name)}" />
  <input type="hidden" name="category_key" value="{escape(category_key)}" />
  <input type="hidden" name="round_name" value="{escape(round_name)}" />
  <input type="hidden" name="left_team_name" value="{escape(left_name)}" />
  <input type="hidden" name="right_team_name" value="{escape(right_name)}" />
  <input type="hidden" name="left_start_order" value="{left_seed}" />
  <input type="hidden" name="right_start_order" value="{right_seed}" />
  <input type="hidden" name="left_status" value="OK" />
  <input type="hidden" name="right_status" value="OK" />
  <div class="h2h-heat-head"><strong>Заезд {spec["match_index"]}</strong></div>
  <div class="h2h-heat-grid">
    {left_row}
    {right_row}
  </div>
  <div class="h2h-heat-footer">
    <label>Буи
      <select name="buoy_penalty_pattern"{disabled_form}>
        {_parallel_buoy_pattern_options(buoy_pattern)}
      </select>
    </label>
    <span class="subtle">Победитель: {escape(winner_text)}</span>
    <button type="submit" class="stitch-save-btn"{disabled_form}>Сохранить заезд</button>
  </div>
</form>
"""


def _parallel_competitor_row_html(
    side: str,
    team_name: str,
    start_order: int,
    team: Team | None,
    base_time_seconds: int,
    penalty_seconds: int,
    status_value: str,
    is_resolved: bool,
    is_winner: bool,
    is_loser: bool,
    scheduled_start_time: str,
    start_entry: SprintEntry | None,
    db_name: str,
    category_key: str,
    show_start_time: bool,
) -> str:
    total = base_time_seconds + penalty_seconds
    row_class = "h2h-row"
    if is_winner:
        row_class += " winner"
    if is_loser:
        row_class += " loser"
    disabled_attr = "" if is_resolved else ' disabled="disabled"'
    team_number = str(team.start_number) if team is not None else ""
    team_link = f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}&open_team={quote(team_name)}"
    start_time_value = scheduled_start_time or (start_entry.start_time if start_entry else "")
    start_cell = (
        f'<div class="h2h-start-cell"><input class="inline-time" data-time-mask="hhmm" name="scheduled_start_time" value="{escape(start_time_value)}" placeholder="10:00"{disabled_attr} /></div>'
        if show_start_time
        else ""
    )
    return f"""
  <div class="{row_class}">
  {start_cell}
  <div class="h2h-no-cell">№ {escape(team_number or '-')}</div>
  <div class="h2h-main-cell">
    <div class="h2h-team-name"><a href="{team_link}">{escape(team_name)}</a></div>
    <div class="h2h-region">{escape(team.region if team is not None else '')}</div>
  </div>
  <div class="h2h-time-cell">
    <input class="inline-time" data-time-mask="mmss" name="{side}_base_time_seconds" value="{_format_mmss(base_time_seconds)}" placeholder="00:00"{disabled_attr} />
    <input value="{_format_mmss(penalty_seconds)}" readonly="readonly" />
    <input value="{_format_mmss(total)}" readonly="readonly" />
  </div>
</div>
"""


def _parallel_resolved_heat_participants(
    spec: dict[str, object],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> dict[str, object]:
    left_name, left_actual, left_seed = _parallel_resolve_source(spec["left_source"], heat_meta, saved_by_round)
    right_name, right_actual, right_seed = _parallel_resolve_source(spec["right_source"], heat_meta, saved_by_round)
    return {
        "left_name": left_name,
        "right_name": right_name,
        "left_is_actual": left_actual,
        "right_is_actual": right_actual,
        "left_seed": left_seed,
        "right_seed": right_seed,
    }


def _parallel_resolve_source(
    source: object,
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> tuple[str, bool, int]:
    if not isinstance(source, tuple) or len(source) != 2:
        return ("Ожидание результата", False, 0)
    kind, value = source
    if kind == "team":
        if isinstance(value, tuple) and len(value) == 2:
            return (str(value[0]), True, int(value[1]))
        return (str(value), True, 0)
    if not isinstance(value, str):
        return ("Ожидание результата", False, 0)
    heat = saved_by_round.get(value)
    meta = heat_meta.get(value)
    if kind == "winner":
        if heat and meta and meta.winner_team_name:
            winner = meta.winner_team_name
            start_order = heat[0].start_order if heat[0].team_name == winner else heat[1].start_order
            return (winner, True, start_order)
        if value.startswith("stage1_seed_"):
            seed = value.removeprefix("stage1_seed_")
            return (f"Победитель за {seed} место", False, int(seed or 0))
        return (f"Победитель {value}", False, 0)
    if kind == "loser":
        if heat and meta and meta.winner_team_name:
            if heat[0].team_name == meta.winner_team_name:
                return (heat[1].team_name, True, heat[1].start_order)
            return (heat[0].team_name, True, heat[0].start_order)
        return (f"Проигравший {value}", False, 0)
    return ("Ожидание результата", False, 0)


def _long_race_start_order(db_path: Path, category_key: str, teams: list[Team]) -> list[Team]:
    sprint_ranked = rank_sprint_entries(
        [
            SprintEntry(
                team_name=entry.team_name,
                start_order=entry.start_order,
                start_time=entry.start_time,
                base_time_seconds=entry.base_time_seconds,
                buoy_penalty_seconds=entry.buoy_penalty_seconds,
                behavior_penalty_seconds=entry.behavior_penalty_seconds,
                status=_normalize_sprint_status(entry.status),
            )
            for entry in load_sprint_entries(db_path, category_key)
        ]
    )
    sprint_points = _points_from_ranked_entries("sprint", sprint_ranked)
    parallel_points = _parallel_sprint_points_map(load_parallel_sprint_heats(db_path, category_key))
    slalom_runs = load_slalom_runs(db_path, category_key)
    slalom_points = _slalom_points_map(slalom_runs)
    slalom_places = _slalom_places_map(slalom_runs)
    return sorted(
        teams,
        key=lambda team: (
            -(
                sprint_points.get(team.name, 0)
                + parallel_points.get(team.name, 0)
                + slalom_points.get(team.name, 0)
            ),
            slalom_places.get(team.name, 9999),
            team.start_number,
            team.name,
        ),
    )


def _page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,700&family=Noto+Serif:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <title>{escape(title)}</title>
    <style>
      :root {{
        --bg: #fbf9f3;
        --panel: #f5f4ec;
        --panel2: #efeee5;
        --line: rgba(177,179,167,0.4);
        --line2: rgba(177,179,167,0.15);
        --text: #31332b;
        --muted: #5e6056;
        --ok: #386948;
        --warn: #c78a16;
        --danger: #9e422c;
        --primary: #645d53;
        --primary-bg: #ebe1d3;
      }}
      * {{ box-sizing: border-box; }}
      #save-toast {{
        position: fixed;
        bottom: 28px;
        right: 28px;
        background: #2a7a2a;
        color: #fff;
        padding: 12px 22px;
        border-radius: 6px;
        font-family: Georgia, serif;
        font-size: 15px;
        opacity: 0;
        transform: translateY(12px);
        transition: opacity 0.25s, transform 0.25s;
        pointer-events: none;
        z-index: 9999;
      }}
      #save-toast.save-toast-show {{
        opacity: 1;
        transform: translateY(0);
      }}
      body {{
        margin: 0;
        font-family: 'Noto Serif', Georgia, serif;
        color: var(--text);
        background: var(--bg);
        -webkit-font-smoothing: antialiased;
      }}
      main {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 32px 24px 56px;
      }}
      h1, h2, h3, p {{ margin: 0; }}
      h1, h2, h3 {{ font-family: 'Newsreader', Georgia, serif; }}
      .hero {{
        display: flex;
        justify-content: space-between;
        gap: 24px;
        align-items: flex-start;
        margin-bottom: 24px;
        padding: 24px;
        background: var(--panel);
        border-bottom: 1px solid var(--line);
      }}
      .hero.compact {{ margin-bottom: 18px; }}
      .eyebrow {{
        font-size: 12px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 10px;
      }}
      h1 {{
        font-size: 52px;
        line-height: 0.96;
        margin-bottom: 10px;
      }}
      .subtle {{
        color: var(--muted);
        max-width: 44ch;
      }}
      .meta {{
        min-width: 220px;
        padding-top: 8px;
      }}
      .meta p {{
        margin-bottom: 8px;
        color: var(--muted);
      }}
      .social-links {{
        display: flex;
        gap: 8px;
        margin-top: 10px;
        flex-wrap: wrap;
      }}
      .icon-link {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 44px;
        height: 34px;
        padding: 0 10px;
        border: 1px solid var(--line);
        background: #fff;
        color: var(--text);
        text-decoration: none;
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}
      .actions-grid, .workspace-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 16px;
      }}
      .category-stack {{
        display: grid;
        gap: 16px;
      }}
      .action-card, .workspace-card {{
        display: block;
        text-decoration: none;
        color: inherit;
        min-height: 180px;
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 18px;
      }}
      .action-card h2, .workspace-card h2 {{
        font-size: 26px;
        line-height: 1.02;
        margin-bottom: 10px;
      }}
      .workspace-card.ok {{ border-left: 8px solid var(--ok); }}
      .workspace-card.warn {{ border-left: 8px solid var(--warn); }}
      .workspace-card.danger {{ border-left: 8px solid var(--danger); }}
      .workspace-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 12px;
      }}
      .status-pill {{
        display: inline-block;
        padding: 6px 10px;
        font-size: 12px;
        line-height: 1.1;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border: 1px solid currentColor;
        max-width: 140px;
      }}
      .status-pill.ok {{ color: var(--ok); }}
      .status-pill.warn {{ color: var(--warn); }}
      .status-pill.danger {{ color: var(--danger); }}
      .stack-form {{
        display: grid;
        gap: 8px;
      }}
      .date-stack {{
        display: grid;
        gap: 8px;
      }}
      .compact-head {{
        margin-bottom: 0;
      }}
      .organizer-row {{
        display: flex;
        gap: 6px;
        align-items: center;
      }}
      .organizer-row input {{
        flex: 1;
        width: auto;
        min-width: 0;
      }}
      .remove-item-btn {{
        flex-shrink: 0;
        width: auto;
        background: none;
        border: 1px solid var(--line);
        border-radius: 4px;
        color: var(--muted);
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
        padding: 4px 9px;
      }}
      .remove-item-btn:hover {{
        border-color: #c00;
        color: #c00;
      }}
      input.order-conflict {{
        border-color: #c00 !important;
        background: #fff0f0 !important;
        color: #c00;
      }}
      .order-conflict-hint {{
        color: #c00;
        font-size: 13px;
        margin-top: 4px;
        display: none;
      }}
      .order-conflict-hint.visible {{
        display: block;
      }}
      .compact-list {{
        margin: 12px 0 0;
        padding-left: 18px;
      }}
      .archive-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 10px;
      }}
      .archive-row a:first-child {{
        flex: 1;
      }}
      .delete-link {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        text-decoration: none;
        color: var(--danger);
        border: 1px solid #d7b8b3;
        background: #fff6f4;
        font-size: 22px;
        line-height: 1;
      }}
      .compact-list.roomy li {{
        margin-bottom: 10px;
      }}
      .export-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      }}
      .export-row-actions {{
        display: flex;
        gap: 12px;
        flex-shrink: 0;
      }}
      .protocol-download-actions {{
        display: flex;
        gap: 8px;
      }}
      .panel-page {{
        display: grid;
        gap: 18px;
      }}
      .panel-page.narrow {{
        max-width: 760px;
      }}
      .page-head {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
        padding: 20px 22px;
        border-bottom: 1px solid var(--line);
        background: var(--panel);
      }}
      .panel-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
      }}
      .panel-card {{
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 18px;
      }}
      .panel-card h2 {{
        font-size: 24px;
        margin-bottom: 14px;
      }}
      .section-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 14px;
      }}
      .inner-block {{
        display: grid;
        gap: 10px;
        padding: 14px;
        border: 1px solid #e7dfd0;
        background: #fcfaf5;
      }}
      .inner-block summary {{
        cursor: pointer;
        list-style: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        font-size: 18px;
        font-weight: 700;
      }}
      .inner-block summary::-webkit-details-marker {{
        display: none;
      }}
      .inner-block[open] summary {{
        margin-bottom: 10px;
      }}
      .summary-note {{
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      .options-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 8px 12px;
      }}
      .option-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        padding: 8px 10px;
        border: 1px solid #e7dfd0;
        background: #fff;
      }}
      .option-row input {{
        width: auto;
        margin: 0;
      }}
      .info-list {{
        display: grid;
        gap: 12px;
      }}
      .info-list div {{
        display: grid;
        gap: 4px;
        padding-bottom: 10px;
        border-bottom: 1px solid #e7dfd0;
      }}
      .info-list dt {{
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      .info-list dd {{
        margin: 0;
      }}
      .confirm-text {{
        font-size: 24px;
        margin-bottom: 16px;
      }}
      .confirm-actions {{
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
      }}
      .judge-grid {{
        display: grid;
        gap: 8px;
        margin-bottom: 16px;
      }}
      .team-form-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 10px;
        margin-bottom: 14px;
      }}
      .team-card-list {{
        display: grid;
        gap: 12px;
      }}
      .team-card {{
        border: 1px solid #e7dfd0;
        background: #fcfaf5;
        padding: 14px;
      }}
      .h2h-board {{
        display: flex;
        gap: 24px;
        align-items: flex-start;
        overflow-x: auto;
        padding-bottom: 10px;
        scrollbar-width: thin;
      }}
      .h2h-column {{
        flex: 0 0 auto;
        display: grid;
        gap: 10px;
      }}
      .h2h-start-column {{
        width: 610px;
      }}
      .h2h-column-body {{
        display: grid;
        gap: 12px;
      }}
      .h2h-heat-card {{
        border: 0;
        background: transparent;
        padding: 0;
        display: grid;
        gap: 6px;
        position: relative;
        width: 486px;
      }}
      .h2h-heat-card::after {{
        content: "";
        position: absolute;
        right: -24px;
        top: 50%;
        width: 24px;
        border-top: 1px solid #2b2b2b;
        pointer-events: none;
      }}
      .h2h-column:last-child .h2h-heat-card::after {{
        display: none;
      }}
      .h2h-heat-head,
      .h2h-heat-footer {{
        display: flex;
        justify-content: space-between;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
      }}
      .h2h-heat-head {{
        min-height: 24px;
        font-size: 12px;
        color: var(--muted);
      }}
      .h2h-heat-footer {{
        align-items: end;
        padding-left: 132px;
      }}
      .h2h-heat-grid {{
        display: grid;
        gap: 0;
      }}
      .h2h-row {{
        display: grid;
        grid-template-columns: 104px 66px 210px 106px;
        border: 1px solid #1f1f1f;
        background: #fff;
      }}
      .h2h-row + .h2h-row {{
        border-top: 0;
      }}
      .h2h-row.preview {{
        grid-template-columns: 72px 328px 86px;
      }}
      .h2h-row.winner {{
        border-color: var(--ok);
        background: #f2faf2;
      }}
      .h2h-row.winner .h2h-team-name {{
        color: var(--ok);
      }}
      .h2h-row.winner .h2h-time-total {{
        color: var(--ok);
      }}
      .h2h-row.loser {{
        border-color: #c98d8d;
        background: #fff1f1;
      }}
      .h2h-row.loser .h2h-team-name {{
        color: var(--danger);
      }}
      .h2h-row.loser .h2h-time-total {{
        color: var(--danger);
      }}
      .h2h-start-cell,
      .h2h-no-cell,
      .h2h-main-cell,
      .h2h-time-cell {{
        padding: 6px 8px;
        border-right: 1px solid #1f1f1f;
      }}
      .h2h-time-cell {{
        border-right: 0;
      }}
      .h2h-start-cell,
      .h2h-no-cell {{
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .h2h-no-cell {{
        font-weight: 700;
        text-align: center;
      }}
      .h2h-team-name {{
        font-size: 15px;
        line-height: 1.05;
        font-weight: 700;
      }}
      .h2h-team-name a {{
        color: inherit;
        text-decoration: none;
        position: relative;
        z-index: 2;
      }}
      .h2h-main-link {{
        color: inherit;
        text-decoration: none;
        display: grid;
        align-content: center;
      }}
      .h2h-region {{
        font-size: 12px;
        color: var(--muted);
        margin-top: 2px;
      }}
      .h2h-time-cell {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 4px;
        align-content: center;
      }}
      .h2h-row.preview .h2h-time-cell {{
        grid-template-columns: 1fr;
        justify-items: center;
        align-items: center;
      }}
      .h2h-time-total {{
        width: 100%;
        text-align: center;
        font-weight: 700;
        font-size: 16px;
      }}
      .h2h-time-cell input,
      .h2h-time-cell select {{
        font-size: 12px;
        min-width: 0;
      }}
      .parallel-lineup-panel {{
        max-width: 760px;
      }}
      .parallel-result-panel {{
        max-width: 760px;
      }}
      .h2h-column .parallel-result-panel {{
        margin-top: 12px;
        max-width: 486px;
      }}
      .parallel-lineup-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 18px;
      }}
      .parallel-lineup-grid .lineup-list li {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 12px;
        align-items: start;
      }}
      .parallel-result-panel .team-form-grid {{
        grid-template-columns: repeat(4, minmax(0, 1fr));
        align-items: end;
      }}
      .parallel-result-panel input,
      .parallel-result-panel select {{
        width: 100%;
      }}
      .h2h-column > h2 {{
        font-size: 20px;
        position: sticky;
        top: 0;
        background: var(--bg);
        padding-bottom: 4px;
        z-index: 1;
      }}
      .h2h-column > .compact-head {{
        position: sticky;
        top: 0;
        background: var(--bg);
        z-index: 1;
        padding-bottom: 4px;
        align-items: center;
      }}
      .h2h-column > .compact-head h2 {{
        margin: 0;
        font-size: 20px;
      }}
      .protocol-table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
      }}
      .protocol-table th,
      .protocol-table td {{
        border: 1px solid #e7dfd0;
        padding: 6px;
        vertical-align: top;
      }}
      .protocol-table th {{
        text-align: left;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        background: var(--panel2);
        color: var(--muted);
        border-bottom: 2px solid var(--line);
      }}
      .protocol-table input,
      .protocol-table select {{
        width: 100%;
        min-width: 0;
      }}
      .protocol-table .col-pp,
      .protocol-table .col-number {{
        width: 70px;
      }}
      .protocol-table .col-time {{
        width: 92px;
      }}
      .protocol-table .col-place {{
        width: 68px;
      }}
      .protocol-table .col-status {{
        width: 98px;
      }}
      .inline-time {{
        width: 82px !important;
      }}
      .crew-cell {{
        font-size: 12px;
        line-height: 1.35;
        color: var(--muted);
      }}
      .slalom-page {{
        width: max-content;
        min-width: 100%;
        gap: 4px;
      }}
      .slalom-sheet-panel {{
        padding: 10px;
        width: max-content;
        margin-top: 0;
      }}
      .slalom-schedule-form {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px 12px;
        align-items: end;
        margin-top: 8px;
      }}
      .slalom-schedule-field {{
        display: grid;
        gap: 4px;
        width: auto;
      }}
      .slalom-schedule-field span {{
        font-size: 12px;
        color: var(--muted);
      }}
      .slalom-schedule-field input {{
        width: 118px;
        height: 34px;
        padding: 6px 8px;
      }}
      .slalom-schedule-submit {{
        width: auto;
        min-width: 180px;
        height: 34px;
        padding: 6px 12px;
        align-self: end;
      }}
      .slalom-clear-button {{
        width: auto;
        min-width: 0;
        height: 34px;
        padding: 6px 12px;
        align-self: end;
      }}
      .slalom-sheet {{
        width: max-content;
        border-collapse: collapse;
        table-layout: auto;
        white-space: nowrap;
      }}
      .slalom-sheet th,
      .slalom-sheet td {{
        border: 1px solid #b0aba3;
        padding: 3px 6px;
        vertical-align: middle;
        background: #fff;
        line-height: 1.1;
      }}
      .slalom-sheet th {{
        font-size: 12px;
        font-weight: 600;
        background: #dedad3;
      }}
      .slalom-sheet .slalom-no,
      .slalom-sheet .slalom-place {{
        width: 82px;
        text-align: center;
        background: #7fa844 !important;
        color: #111;
        vertical-align: middle;
        padding: 0;
        position: relative;
      }}
      .slalom-sheet .slalom-no-idle {{
        background: #fff !important;
      }}
      .slalom-sheet .slalom-no-partial {{
        background: #d7c85b !important;
      }}
      .slalom-sheet .slalom-no-complete {{
        background: #7fa844 !important;
      }}
      .slalom-sheet .slalom-no-label,
      .slalom-sheet .slalom-place-label {{
        font-size: 10px;
        font-weight: 400;
        opacity: 0.9;
        letter-spacing: 0.03em;
      }}
      .slalom-sheet .slalom-no-value,
      .slalom-sheet .slalom-place-value {{
        font-size: 24px;
        font-weight: 700;
        line-height: 1;
      }}
      .slalom-sheet .slalom-place-stack {{
        display: grid;
        grid-template-rows: repeat(3, 1fr);
        height: 100%;
        min-height: 152px;
      }}
      .slalom-sheet .slalom-place-row {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 5px;
        border-bottom: 1px solid rgba(255,255,255,0.35);
        padding: 6px 4px;
      }}
      .slalom-sheet .slalom-place-row:last-child {{
        border-bottom: 0;
      }}
      .slalom-sheet .slalom-place-metric {{
        font-size: 16px;
        font-weight: 700;
        line-height: 1;
      }}
      .slalom-sheet .slalom-team-block {{
        min-width: 280px;
        padding: 0;
        background: #fff !important;
      }}
      .slalom-sheet .slalom-team-stack {{
        display: grid;
        grid-template-rows: repeat(3, 1fr);
        height: 152px;
      }}
      .slalom-sheet .slalom-name,
      .slalom-sheet .slalom-subject,
      .slalom-sheet .slalom-lineup {{
        padding: 6px 10px;
        display: flex;
        align-items: center;
      }}
      .slalom-sheet .slalom-name {{
        font-size: 15px;
        font-weight: 700;
        white-space: nowrap;
        background: #f5c4b0 !important;
      }}
      .slalom-sheet .slalom-subject {{
        font-size: 12px;
        color: var(--muted);
        background: #ccc9c3 !important;
      }}
      .slalom-sheet .slalom-lineup {{
        font-size: 12px;
        background: #ede97a !important;
      }}
      .slalom-sheet .slalom-lineup-label {{
        display: block;
        margin-bottom: 3px;
        font-weight: 700;
        color: var(--text);
      }}
      .slalom-sheet .slalom-lineup-link {{
        font-weight: 700;
      }}
      .slalom-sheet .slalom-attempt-head,
      .slalom-sheet .slalom-attempt-name {{
        width: 88px;
        font-weight: 600;
        white-space: nowrap;
        text-align: center;
        background: #dedad3;
      }}
      .slalom-sheet .slalom-attempt-spacer {{
        background: #fafaf8;
        text-align: center;
        vertical-align: middle;
      }}
      .slalom-sheet .slalom-gate,
      .slalom-sheet .slalom-start-finish {{
        width: 64px;
        min-width: 64px;
        text-align: center;
      }}
      .slalom-sheet td.slalom-gate,
      .slalom-sheet td.slalom-start-finish {{
        background: #fafaf8;
      }}
      .slalom-sheet .slalom-attempt-header-row,
      .slalom-sheet .slalom-attempt-value-row {{
        height: 38px;
      }}
      .slalom-sheet .slalom-attempt-best th,
      .slalom-sheet .slalom-attempt-best td {{
        background: #f5f9ee;
      }}
      .slalom-sheet .slalom-best-badge {{
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        color: #5d7b2c;
        letter-spacing: 0.02em;
      }}
      .slalom-sheet .slalom-attempt-header-row {{
        height: 38px;
      }}
      .slalom-sheet .protocol-crew {{
        font-size: 12px;
        line-height: 1.15;
      }}
      .slalom-sheet input,
      .slalom-sheet select,
      .slalom-sheet button {{
        width: 100%;
        min-width: 0;
      }}
      .slalom-sheet input,
      .slalom-sheet select {{
        height: 28px;
        padding: 2px 6px;
        background: #fff;
        border: 1px solid #c0bbb3;
        border-radius: 2px;
      }}
      .slalom-penalty-picker {{
        position: relative;
      }}
      .slalom-penalty-trigger {{
        width: 100%;
        height: 28px;
        padding: 2px 6px;
        border: 1px solid #c0bbb3;
        border-radius: 2px;
        background: #fff;
        font: inherit;
        line-height: 1;
        text-align: center;
        cursor: pointer;
      }}
      .slalom-penalty-menu {{
        position: absolute;
        top: calc(100% + 2px);
        left: 0;
        display: none;
        grid-template-columns: 1fr;
        min-width: 100%;
        border: 1px solid #c0bbb3;
        background: #fff;
        z-index: 5;
      }}
      .slalom-penalty-picker.open .slalom-penalty-menu {{
        display: grid;
      }}
      .slalom-penalty-option {{
        border: 0;
        border-top: 1px solid #e2ddd5;
        background: #fff;
        padding: 4px 6px;
        font: inherit;
        text-align: center;
        cursor: pointer;
      }}
      .slalom-penalty-option:first-child {{
        border-top: 0;
      }}
      .slalom-sheet select {{
        appearance: none;
      }}
      .slalom-card-gap > td {{
        height: 10px;
        background: transparent !important;
        border: none !important;
        padding: 0;
      }}
      .slalom-lineup-panel {{
        margin-top: 12px;
      }}
      .h2h-start-node {{
        display: grid;
        grid-template-columns: 104px 382px;
        width: 486px;
        border: 1px solid #2b2b2b;
        background: #fff;
        box-sizing: border-box;
        overflow: hidden;
      }}
      .h2h-start-node-time {{
        display: grid;
        align-content: center;
        gap: 6px;
        padding: 6px 8px;
        border-right: 1px solid #2b2b2b;
        background: #fff;
      }}
      .h2h-start-node-time .subtle {{
        font-size: 12px;
        color: var(--text);
      }}
      .h2h-start-node-time input {{
        width: 100%;
        height: 34px;
      }}
      .h2h-start-node-main {{
        display: grid;
        grid-template-rows: 42px 34px;
        min-width: 0;
      }}
      .h2h-start-node-top {{
        display: grid;
        grid-template-columns: 66px minmax(0, 1fr);
        min-width: 0;
        border-bottom: 1px solid #2b2b2b;
      }}
      .h2h-start-node-number,
      .h2h-start-node-name {{
        padding: 6px 8px;
        background: #fff;
      }}
      .h2h-start-node-number {{
        display: flex;
        align-items: center;
        justify-content: center;
        border-right: 1px solid #2b2b2b;
        font-weight: 700;
      }}
      .h2h-start-node-name {{
        display: grid;
        align-content: center;
      }}
      .h2h-start-node-name a {{
        font-size: 15px;
        line-height: 1.1;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: inherit;
        text-decoration: none;
      }}
      .h2h-start-node-bottom {{
        display: grid;
        align-content: center;
        padding: 6px 8px;
      }}
      .h2h-start-node-bottom a {{
        color: var(--text);
        text-decoration: underline;
        text-underline-offset: 3px;
      }}
      .lineup-member-name {{
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }}
      .sr-only {{
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }}
      .protocol-page {{
        gap: 14px;
      }}
      .protocol-head {{
        position: relative;
        justify-content: center;
        text-align: center;
      }}
      .protocol-title-block {{
        display: grid;
        gap: 4px;
        justify-items: center;
      }}
      .protocol-back {{
        position: absolute;
        left: 22px;
        top: 20px;
      }}
      .protocol-summary .summary-grid {{
        justify-items: center;
        text-align: center;
      }}
      .protocol-footer {{
        padding-top: 22px;
        padding-bottom: 26px;
      }}
      .protocol-signatures {{
        display: grid;
        grid-template-columns: repeat(2, minmax(240px, 1fr));
        gap: 36px;
      }}
      .protocol-signature {{
        display: grid;
        gap: 8px;
      }}
      .protocol-signature dt {{
        font-size: 14px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      .protocol-signature dd {{
        margin: 0;
        font-size: 20px;
        font-weight: 700;
      }}
      .protocol-table-results .col-pp {{
        width: 38px;
      }}
      .protocol-table-results .col-number {{
        width: 26px;
      }}
      .protocol-table-results .col-time {{
        width: 74px;
      }}
      .protocol-table-results .col-place {{
        width: 52px;
      }}
      .protocol-table-results th:nth-child(3),
      .protocol-table-results td:nth-child(3) {{
        width: 150px;
      }}
      .protocol-table-results th:nth-child(4),
      .protocol-table-results td:nth-child(4) {{
        width: 300px;
      }}
      .protocol-table-results th:nth-child(5),
      .protocol-table-results td:nth-child(5) {{
        width: 150px;
      }}
      .protocol-table-results th:nth-child(9),
      .protocol-table-results td:nth-child(9) {{
        padding-right: 10px;
      }}
      .protocol-table-results th:nth-child(10),
      .protocol-table-results td:nth-child(10) {{
        padding-left: 10px;
      }}
      .protocol-table-results th,
      .protocol-table-results td {{
        padding: 5px;
      }}
      .protocol-table-results .protocol-crew {{
        white-space: nowrap;
      }}
      .protocol-table-slalom-sheet {{
        width: max-content;
        min-width: 100%;
        table-layout: fixed;
      }}
      .protocol-table-slalom-sheet .slalom-col-number {{
        width: 42px;
      }}
      .protocol-table-slalom-sheet .slalom-col-team {{
        width: 140px;
      }}
      .protocol-table-slalom-sheet .slalom-col-subject {{
        width: 115px;
      }}
      .protocol-table-slalom-sheet .slalom-col-crew {{
        width: 320px;
      }}
      .protocol-table-slalom-sheet .slalom-col-attempt {{
        width: 86px;
      }}
      .protocol-table-slalom-sheet .slalom-col-start,
      .protocol-table-slalom-sheet .slalom-col-finish,
      .protocol-table-slalom-sheet .slalom-col-total {{
        width: 66px;
      }}
      .protocol-table-slalom-sheet .slalom-col-place {{
        width: 50px;
      }}
      .protocol-table-slalom-sheet .slalom-gate-colgroup {{
        width: 30px;
      }}
      .protocol-table-slalom-sheet th,
      .protocol-table-slalom-sheet td {{
        padding: 4px 5px;
        font-size: 12px;
        line-height: 1.2;
        vertical-align: middle;
      }}
      .protocol-table-slalom-sheet .col-number {{
        text-align: center;
        vertical-align: middle;
      }}
      .protocol-table-slalom-sheet .col-place {{
        text-align: center;
        vertical-align: middle;
      }}
      .protocol-table-slalom-sheet .protocol-crew {{
        white-space: nowrap;
      }}
      .protocol-table-slalom-sheet .protocol-slalom-subject {{
        font-size: 12px;
        line-height: 1.2;
        color: var(--text);
        font-weight: 400;
      }}
      .protocol-table-slalom-sheet .slalom-attempt-col,
      .protocol-table-slalom-sheet .slalom-attempt-name {{
        white-space: nowrap;
      }}
      .protocol-table-slalom-sheet .slalom-attempt-name {{
        font-weight: 700;
      }}
      .protocol-table-slalom-sheet .slalom-best-attempt-note {{
        display: inline;
        margin-left: 4px;
        font-size: 11px;
        font-weight: 400;
        color: var(--muted);
      }}
      .protocol-table-slalom-sheet .col-time {{
        text-align: center;
      }}
      .protocol-table-slalom-sheet .slalom-gate-col,
      .protocol-table-slalom-sheet .slalom-gate-value {{
        text-align: center;
      }}
      .protocol-table-slalom-sheet .slalom-protocol-attempt td {{
        height: 32px;
      }}
      .protocol-table-slalom-sheet .slalom-protocol-attempt.best .slalom-attempt-name,
      .protocol-table-slalom-sheet .slalom-protocol-attempt.best .col-time,
      .protocol-table-slalom-sheet .slalom-protocol-attempt.best .slalom-gate-value {{
        background: rgba(164, 190, 132, 0.14);
      }}
      .protocol-table-slalom-sheet .slalom-protocol-attempt-1 td {{
        border-top: 2px solid rgba(80, 68, 47, 0.24);
      }}
      .protocol-table-slalom-sheet tbody tr:first-child td {{
        border-top-width: 1px;
      }}
      .protocol-table-slalom-sheet .slalom-protocol-attempt-2 td {{
        border-bottom: 2px solid rgba(80, 68, 47, 0.24);
      }}
      .protocol-table-slalom-sheet .slalom-protocol-attempt-1 .col-number,
      .protocol-table-slalom-sheet .slalom-protocol-attempt-1 .col-place,
      .protocol-table-slalom-sheet .slalom-protocol-attempt-2 .col-number,
      .protocol-table-slalom-sheet .slalom-protocol-attempt-2 .col-place {{
        border-top: 2px solid rgba(80, 68, 47, 0.24);
        border-bottom: 2px solid rgba(80, 68, 47, 0.24);
      }}
      .protocol-table-combined .col-number {{
        width: 36px;
      }}
      .protocol-table-combined .col-discipline {{
        width: 70px;
        text-align: center;
        vertical-align: middle;
      }}
      .protocol-table-combined th:nth-child(2),
      .protocol-table-combined td:nth-child(2) {{
        width: 120px;
      }}
      .protocol-table-combined th:nth-child(3),
      .protocol-table-combined td:nth-child(3) {{
        width: 300px;
      }}
      .protocol-table-combined th:nth-child(4),
      .protocol-table-combined td:nth-child(4) {{
        width: 150px;
      }}
      .discipline-points {{
        display: inline-block;
        margin-top: 2px;
        font-size: 12px;
        color: var(--muted);
      }}
      .discipline-cell {{
        text-align: center;
        vertical-align: middle !important;
        font-size: 20px;
        font-weight: 700;
      }}
      .discipline-cell .discipline-points {{
        font-size: 14px;
        font-weight: 700;
      }}
      .lineup-summary {{
        display: inline-flex;
        gap: 8px;
        align-items: baseline;
        color: inherit;
      }}
      .lineup-names {{
        border-bottom: 1px dotted #8b7f6e;
      }}
      .lineup-details summary {{
        cursor: pointer;
        list-style: none;
      }}
      .lineup-details summary::-webkit-details-marker {{
        display: none;
      }}
      .lineup-groups {{
        display: grid;
        gap: 8px;
        margin-top: 8px;
      }}
      .lineup-list {{
        margin-top: 4px;
      }}
      .lineup-list li {{
        display: flex;
        justify-content: space-between;
        gap: 8px;
        align-items: baseline;
      }}
      .lineup-warning {{
        font-size: 11px;
      }}
      .link-button {{
        border: 0;
        background: transparent;
        color: #8b7f6e;
        padding: 0;
        font: inherit;
        cursor: pointer;
        text-decoration: underline;
      }}
      .team-card-head {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
      }}
      .team-meta {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 8px 12px;
        margin-top: 12px;
      }}
      .team-actions {{
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }}
      .inline-action {{
        width: auto;
      }}
      .reserve-card {{
        background: #f5f3ee;
        border-color: #ccc8bc;
      }}
      .judge-card {{
        border: 1px solid #e7dfd0;
        background: #fcfaf5;
        padding: 10px 12px;
      }}
      .judge-card h3 {{
        margin: 0 0 12px;
        font-size: 19px;
      }}
      .judge-card-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 10px;
      }}
      .member-row {{
        display: grid;
        grid-template-columns: 68px minmax(300px, 2fr) 150px 170px;
        gap: 10px;
        align-items: end;
      }}
      .member-index {{
        display: grid;
        gap: 6px;
      }}
      .member-index-value {{
        padding: 10px 12px;
        border: 1px solid var(--line);
        background: #f3efe6;
        color: var(--muted);
      }}
      .year-warning {{
        display: none;
      }}
      .invalid-year {{
        border-color: var(--danger) !important;
        color: var(--danger);
        background: #fff7f6;
      }}
      .card-button {{
        width: auto;
        white-space: nowrap;
        cursor: pointer;
      }}
      input, button {{
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--line);
        background: #fff;
        color: var(--text);
        font: inherit;
      }}
      select {{
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--line);
        background: #fff;
        color: var(--text);
        font: inherit;
      }}
      button, .primary-link, .secondary-link {{
        display: inline-block;
        text-decoration: none;
        padding: 10px 12px;
        border: 1px solid var(--line);
      }}
      .primary-link {{
        background: var(--text);
        color: #fff;
      }}
      .secondary-link {{
        color: var(--text);
        background: transparent;
      }}
      .danger-link {{
        color: var(--danger);
        border-color: #d7b8b3;
        background: #fff6f4;
      }}
      .danger-button {{
        width: auto;
        color: #fff;
        background: var(--danger);
        border-color: var(--danger);
      }}
      /* ── Judges page ──────────────────────────────────── */
      .judges-section {{
        margin-bottom: 36px;
      }}
      .judges-section-head {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        border-bottom: 1px solid var(--line);
        padding-bottom: 8px;
        margin-bottom: 24px;
      }}
      .judges-section-head h2 {{
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--primary);
      }}
      .judges-section-note {{
        font-size: 12px;
        font-style: italic;
        color: var(--muted);
      }}
      .judges-required-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 32px;
      }}
      .judges-role-card {{
        display: flex;
        flex-direction: column;
        gap: 20px;
      }}
      .judges-role-tag {{
        display: inline-block;
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        font-weight: 700;
        background: var(--primary-bg);
        color: var(--primary);
        padding: 4px 8px;
      }}
      .judge-field {{
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}
      .judge-field label {{
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--muted);
        font-weight: 700;
        cursor: pointer;
      }}
      .judge-field input,
      .judge-field select {{
        width: 100%;
        background: transparent;
        border: none;
        border-bottom: 1px solid var(--line);
        padding: 4px 0;
        font-family: 'Noto Serif', Georgia, serif;
        font-size: 15px;
        color: var(--text);
        border-radius: 0;
      }}
      .judge-field input:focus,
      .judge-field select:focus {{
        outline: none;
        border-bottom: 2px solid var(--primary);
      }}
      .judges-extra-list {{
        display: grid;
        gap: 0;
        margin-bottom: 16px;
      }}
      .judges-extra-row {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr auto;
        gap: 16px;
        align-items: end;
        padding: 14px 0;
        border-bottom: 1px solid var(--line2);
      }}
      .judges-extra-row .judge-field {{
        gap: 4px;
      }}
      .judges-remove-btn {{
        background: none;
        border: none;
        color: var(--muted);
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
        cursor: pointer;
        padding: 4px 0;
        width: auto;
        opacity: 0.4;
        align-self: end;
        padding-bottom: 6px;
      }}
      .judges-extra-row:hover .judges-remove-btn {{ opacity: 1; color: var(--danger); }}
      .judges-add-btn {{
        width: 100%;
        background: transparent;
        border: 2px dashed var(--line);
        color: var(--muted);
        font-family: 'Noto Serif', Georgia, serif;
        font-size: 12px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        font-weight: 700;
        padding: 16px;
        cursor: pointer;
        transition: border-color 0.15s, color 0.15s;
      }}
      .judges-add-btn:hover {{
        border-color: var(--ok);
        color: var(--ok);
        background: transparent;
      }}
      .judges-footer {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        border-top: 2px solid var(--primary-bg);
        padding-top: 24px;
        margin-top: 8px;
        flex-wrap: wrap;
      }}
      .judges-status-line {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      .judges-status-dot {{
        width: 10px;
        height: 10px;
        background: var(--ok);
        flex-shrink: 0;
      }}
      /* ─────────────────────────────────────────────────── */
      /* ── Stitch editorial styles ───────────────────────── */
      .stitch-cta {{
        display: inline-block;
        text-decoration: none;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--primary);
        border-bottom: 2px solid var(--primary-bg);
        padding: 4px 0;
        background: transparent;
        border-top: none;
        border-left: none;
        border-right: none;
        cursor: pointer;
        width: auto;
        transition: background 0.15s, padding 0.15s;
      }}
      .stitch-cta:hover {{
        background: var(--primary-bg);
        padding: 4px 8px;
      }}
      .stitch-save-btn {{
        background: var(--ok);
        color: #fff;
        border: none;
        font-family: 'Noto Serif', Georgia, serif;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        padding: 14px 36px;
        width: auto;
        cursor: pointer;
        transition: filter 0.15s;
      }}
      .stitch-save-btn:hover {{ filter: brightness(0.93); }}
      .stitch-save-btn:disabled {{
        background: var(--muted);
        cursor: not-allowed;
        filter: none;
      }}
      .ledger-archive {{ border-top: 1px solid var(--line); }}
      .ledger-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 18px 16px;
        border-bottom: 1px solid var(--line2);
        transition: background 0.12s;
      }}
      .ledger-row:nth-child(even) {{ background: var(--panel); }}
      .ledger-row:hover {{ background: var(--panel2); }}
      .ledger-row .ledger-link {{
        font-size: 18px;
        text-decoration: none;
        color: var(--text);
        flex: 1;
        font-family: 'Newsreader', Georgia, serif;
      }}
      .ledger-row .ledger-link:hover {{ color: var(--primary); }}
      .ledger-row .delete-link {{
        opacity: 0;
        transition: opacity 0.15s;
        border: none;
        background: none;
        font-size: 14px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
        color: var(--danger);
        text-decoration: none;
        padding: 4px 0;
        width: auto;
        cursor: pointer;
      }}
      .ledger-row:hover .delete-link {{ opacity: 1; }}
      .index-hero {{
        border-bottom: 1px solid var(--line);
        padding-bottom: 32px;
        margin-bottom: 48px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 24px;
        flex-wrap: wrap;
      }}
      .index-hero h1 {{
        font-size: 80px;
        line-height: 0.9;
        letter-spacing: -0.02em;
        color: var(--text);
      }}
      .index-meta {{ text-align: right; padding-bottom: 8px; }}
      .index-meta .ver {{
        display: block;
        font-size: 12px;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 4px;
      }}
      .index-meta .author {{
        display: block;
        font-size: 13px;
        font-style: italic;
        color: var(--primary);
      }}
      .index-open-last {{ margin-top: 20px; }}
      .index-layout {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 48px;
      }}
      @media (min-width: 760px) {{
        .index-layout {{ grid-template-columns: 2fr 1fr; }}
      }}
      .section-label {{
        font-size: 11px;
        letter-spacing: 0.3em;
        text-transform: uppercase;
        color: var(--muted);
        font-weight: 700;
        margin-bottom: 24px;
      }}
      .form-panel {{
        background: var(--panel);
        padding: 28px;
        position: sticky;
        top: 24px;
      }}
      .form-panel h3 {{
        font-size: 11px;
        letter-spacing: 0.3em;
        text-transform: uppercase;
        color: var(--muted);
        font-weight: 700;
        margin-bottom: 28px;
      }}
      .form-field {{
        margin-bottom: 28px;
      }}
      .form-field label {{
        display: block;
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 8px;
        font-weight: 700;
      }}
      .editorial-input {{
        width: 100%;
        background: transparent;
        border: none;
        border-bottom: 1px solid var(--line);
        padding: 6px 0;
        font-family: 'Noto Serif', Georgia, serif;
        font-size: 16px;
        color: var(--text);
        border-radius: 0;
        box-shadow: none;
        outline: none;
      }}
      .editorial-input:focus {{
        border-bottom: 2px solid var(--primary);
      }}
      .form-hint {{
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--line2);
        font-size: 13px;
        color: var(--muted);
        font-style: italic;
        line-height: 1.5;
      }}
      .sprint-draw-card {{
        background: var(--panel);
        padding: 20px 22px;
        border-bottom: 1px solid var(--line);
        margin-bottom: 4px;
      }}
      .sprint-draw-grid {{
        display: flex;
        flex-wrap: wrap;
        gap: 20px 32px;
        align-items: flex-end;
      }}
      .draw-field {{
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}
      .draw-field span {{
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--muted);
        font-weight: 700;
      }}
      .draw-field input {{
        width: 110px;
        font-size: 16px;
        padding: 4px 0;
        border: none;
        border-bottom: 1px solid var(--line);
        background: transparent;
        font-family: 'Newsreader', Georgia, serif;
      }}
      .draw-field input:focus {{
        outline: none;
        border-bottom: 2px solid var(--primary);
      }}
      .draw-actions {{
        display: flex;
        gap: 12px;
        align-items: flex-end;
      }}
      .sprint-footer {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding-top: 20px;
        flex-wrap: wrap;
      }}
      /* ─────────────────────────────────────────────────── */
      @media (max-width: 760px) {{
        h1 {{ font-size: 38px; }}
        .hero {{ flex-direction: column; }}
        .meta {{ min-width: 0; }}
        .page-head {{ flex-direction: column; }}
        .protocol-head {{
          justify-content: flex-start;
          text-align: left;
        }}
        .protocol-title-block {{
          justify-items: start;
        }}
        .protocol-back {{
          position: static;
        }}
        .protocol-signatures {{
          grid-template-columns: 1fr;
          gap: 18px;
        }}
        .confirm-actions {{ flex-direction: column; align-items: stretch; }}
        .member-row {{ grid-template-columns: 1fr; }}
        .h2h-board {{
          display: grid;
          grid-template-columns: 1fr;
          overflow-x: visible;
        }}
        .h2h-column {{
          flex-basis: auto;
        }}
        .h2h-row {{ grid-template-columns: 1fr; }}
        .h2h-start-cell,
        .h2h-no-cell,
        .h2h-main-cell {{
          border-right: 0;
          border-bottom: 1px solid #1f1f1f;
        }}
        .h2h-time-cell {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main>{content}</main>
    <script>
      function addJudgeCard() {{
        const container = document.getElementById("judges-list");
        const template = document.getElementById("judge-card-template");
        if (!container || !template) {{
          return;
        }}
        const nextIndex = container.children.length + 1;
        const html = template.innerHTML.replaceAll("__INDEX__", String(nextIndex));
        container.insertAdjacentHTML("beforeend", html);
      }}

      function addCompetitionDay() {{
        const container = document.getElementById("competition-days");
        const template = document.getElementById("competition-day-template");
        if (!container || !template) {{
          return;
        }}
        const nextIndex = container.querySelectorAll("input[name^='competition_date_']").length + 1;
        const html = template.innerHTML.replaceAll("__INDEX__", String(nextIndex));
        container.insertAdjacentHTML("beforeend", html);
      }}

      function addOrganizer() {{
        const container = document.getElementById("organizers-list");
        const template = document.getElementById("organizer-template");
        if (!container || !template) {{
          return;
        }}
        const nextIndex = container.querySelectorAll("input[name^='organizer_']").length + 1;
        const html = template.innerHTML.replaceAll("__INDEX__", String(nextIndex));
        container.insertAdjacentHTML("beforeend", html);
      }}

      function validateMemberYears() {{
        document.querySelectorAll("[data-age-min][data-age-max]").forEach((input) => {{
          const minYear = parseInt(input.dataset.ageMin || "", 10);
          const maxYear = parseInt(input.dataset.ageMax || "", 10);
          const value = parseInt((input.value || "").slice(0, 4), 10);
          const warning = input.parentElement?.querySelector(".year-warning");
          const valid = !Number.isNaN(value) && !Number.isNaN(minYear) && !Number.isNaN(maxYear) && value >= minYear && value <= maxYear;
          if (!input.value) {{
            input.classList.remove("invalid-year");
            input.removeAttribute("title");
            if (warning) warning.textContent = "";
            return;
          }}
          if (!valid) {{
            input.classList.add("invalid-year");
            input.title = "Допустимо: " + String(minYear) + "-" + String(maxYear);
            if (warning) warning.textContent = "";
          }} else {{
            input.classList.remove("invalid-year");
            input.removeAttribute("title");
            if (warning) warning.textContent = "";
          }}
        }});
      }}

      function formatDigitsAsTime(value, mode) {{
        const limit = mode === "hhmmss" ? 6 : 4;
        const digits = (value || "").replace(/\\D/g, "").slice(0, limit);
        if (mode === "hhmmss") {{
          const padded = digits.padStart(6, "0");
          return padded.slice(0, 2) + ":" + padded.slice(2, 4) + ":" + padded.slice(4, 6);
        }}
        if (mode === "hhmm") {{
          const padded = digits.padStart(4, "0");
          return padded.slice(0, 2) + ":" + padded.slice(2, 4);
        }}
        const padded = digits.padStart(4, "0");
        return padded.slice(0, 2) + ":" + padded.slice(2, 4);
      }}

      function normalizeTimeRaw(input) {{
        const limit = input.dataset.timeMask === "hhmmss" ? 6 : 4;
        const raw = (input.dataset.timeRaw || input.value || "").replace(/\\D/g, "").slice(0, limit);
        input.dataset.timeRaw = raw;
        input.value = formatDigitsAsTime(raw, input.dataset.timeMask || "hhmm");
      }}

      function applyTimeMasks() {{
        document.querySelectorAll("input.inline-time, input[data-time-mask]").forEach((input) => {{
          if (!(input instanceof HTMLInputElement) || input.dataset.timeMaskBound === "1") {{
            return;
          }}
          input.dataset.timeMaskBound = "1";
          input.setAttribute("inputmode", "numeric");

          const mask = input.dataset.timeMask || "mmss";
          // character positions of each digit slot inside the formatted string
          const slots = mask === "hhmmss" ? [0, 1, 3, 4, 6, 7] : [0, 1, 3, 4];
          const emptyVal = mask === "hhmmss" ? "00:00:00" : "00:00";

          function buildValue(digits) {{
            const d = digits.join("").padStart(slots.length, "0").slice(0, slots.length);
            return mask === "hhmmss"
              ? d[0]+d[1]+":"+d[2]+d[3]+":"+d[4]+d[5]
              : d[0]+d[1]+":"+d[2]+d[3];
          }}

          function initValue() {{
            const raw = (input.value || "").replace(/\\D/g, "").padStart(slots.length, "0").slice(0, slots.length);
            input.value = buildValue(raw.split(""));
          }}

          function getDigits() {{
            return slots.map((p) => input.value[p] || "0");
          }}

          function setDigits(arr) {{
            input.value = buildValue(arr);
          }}

          function getSlot() {{
            const pos = input.selectionStart ?? 0;
            for (let i = 0; i < slots.length; i++) {{
              if (slots[i] >= pos) return i;
            }}
            return slots.length - 1;
          }}

          function setSlot(i) {{
            const idx = Math.max(0, Math.min(i, slots.length - 1));
            const pos = slots[idx];
            input.setSelectionRange(pos, pos + 1);
          }}

          initValue();

          input.addEventListener("focus", () => setSlot(0));

          input.addEventListener("click", () => {{
            requestAnimationFrame(() => setSlot(getSlot()));
          }});

          input.addEventListener("keydown", (e) => {{
            if (e.key === "Tab") return;
            e.preventDefault();
            const slot = getSlot();
            if (/^\\d$/.test(e.key)) {{
              const d = getDigits();
              d[slot] = e.key;
              setDigits(d);
              setSlot(slot + 1);
              return;
            }}
            if (e.key === "Backspace") {{
              const d = getDigits();
              const target = slot > 0 ? slot - 1 : 0;
              d[target] = "0";
              setDigits(d);
              setSlot(target);
              return;
            }}
            if (e.key === "Delete") {{
              const d = getDigits();
              d[slot] = "0";
              setDigits(d);
              setSlot(slot);
              return;
            }}
            if (e.key === "ArrowLeft")  {{ setSlot(slot - 1); return; }}
            if (e.key === "ArrowRight") {{ setSlot(slot + 1); return; }}
            if (e.key === "Home")  {{ setSlot(0); return; }}
            if (e.key === "End")   {{ setSlot(slots.length - 1); return; }}
          }});

          input.addEventListener("paste", (e) => {{
            e.preventDefault();
            const pasted = (e.clipboardData?.getData("text") || "").replace(/\\D/g, "");
            const d = getDigits();
            let slot = getSlot();
            for (const ch of pasted) {{
              if (slot >= slots.length) break;
              d[slot++] = ch;
            }}
            setDigits(d);
            setSlot(Math.min(slot, slots.length - 1));
          }});

          input.addEventListener("blur", () => {{
            const d = getDigits();
            setDigits(d);
          }});
        }});
      }}

      function applySlalomPenaltyPickers() {{
        document.querySelectorAll(".slalom-penalty-picker").forEach((picker) => {{
          if (!(picker instanceof HTMLElement) || picker.dataset.bound === "1") {{
            return;
          }}
          const hidden = picker.querySelector("input[type='hidden']");
          const trigger = picker.querySelector(".slalom-penalty-trigger");
          const options = picker.querySelectorAll(".slalom-penalty-option");
          if (!(hidden instanceof HTMLInputElement) || !(trigger instanceof HTMLButtonElement)) {{
            return;
          }}
          trigger.addEventListener("click", (event) => {{
            event.preventDefault();
            document.querySelectorAll(".slalom-penalty-picker.open").forEach((openPicker) => {{
              if (openPicker !== picker) {{
                openPicker.classList.remove("open");
              }}
            }});
            picker.classList.toggle("open");
          }});
          options.forEach((option) => {{
            option.addEventListener("click", (event) => {{
              event.preventDefault();
              if (!(option instanceof HTMLButtonElement)) {{
                return;
              }}
              const value = option.dataset.value || "0";
              hidden.value = value;
              trigger.textContent = value;
              picker.classList.remove("open");
              const owner = hidden.form;
              if (owner instanceof HTMLFormElement) {{
                recalcSlalomSheet();
                submitSlalomForm(owner);
              }}
            }});
          }});
          picker.dataset.bound = "1";
        }});
        document.addEventListener("click", (event) => {{
          if (!(event.target instanceof Element)) {{
            return;
          }}
          document.querySelectorAll(".slalom-penalty-picker.open").forEach((openPicker) => {{
            if (!openPicker.contains(event.target)) {{
              openPicker.classList.remove("open");
            }}
          }});
        }}, {{ once: true }});
      }}

      async function submitSlalomForm(form) {{
        if (!(form instanceof HTMLFormElement) || form.dataset.submitting === "1") {{
          return;
        }}
        form.dataset.submitting = "1";
        try {{
          await fetch(form.action, {{
            method: form.method || "POST",
            body: new FormData(form),
            redirect: "follow",
          }});
        }} finally {{
          form.dataset.submitting = "0";
        }}
      }}

      function parseHhmmssValue(value) {{
        const parts = String(value || "").split(":");
        if (parts.length !== 3) {{
          return 0;
        }}
        const hours = Number(parts[0] || 0);
        const minutes = Number(parts[1] || 0);
        const seconds = Number(parts[2] || 0);
        if (Number.isNaN(hours) || Number.isNaN(minutes) || Number.isNaN(seconds)) {{
          return 0;
        }}
        return hours * 3600 + minutes * 60 + seconds;
      }}

      function formatMmssValue(totalSeconds) {{
        const safe = Math.max(0, Number(totalSeconds) || 0);
        const minutes = Math.floor(safe / 60);
        const seconds = safe % 60;
        return String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
      }}

      function getSlalomFormRows(formId) {{
        return Array.from(document.querySelectorAll(`[data-slalom-form="${{formId}}"]`));
      }}

      function getSlalomFormField(form, name) {{
        if (!(form instanceof HTMLFormElement)) {{
          return null;
        }}
        return document.querySelector(`[form="${{form.id}}"][name="${{name}}"]`);
      }}

      function getSlalomFormFields(form, prefix) {{
        if (!(form instanceof HTMLFormElement)) {{
          return [];
        }}
        return Array.from(document.querySelectorAll(`[form="${{form.id}}"][name^="${{prefix}}"]`));
      }}

      function setSlalomAttemptBest(formId, attemptNumber, isBest) {{
        getSlalomFormRows(formId)
          .filter((row) => row.getAttribute("data-slalom-attempt") === String(attemptNumber))
          .forEach((row) => {{
            row.classList.toggle("slalom-attempt-best", isBest);
          }});
        const valueRow = getSlalomFormRows(formId).find((row) =>
          row.classList.contains("slalom-attempt-value-row") &&
          row.getAttribute("data-slalom-attempt") === String(attemptNumber)
        );
        const badgeCell = valueRow ? valueRow.querySelector("[data-slalom-best-cell]") : null;
        if (badgeCell instanceof HTMLElement) {{
          badgeCell.innerHTML = isBest ? '<span class="slalom-best-badge">лучшая</span>' : "";
        }}
      }}

      function evaluateSlalomAttempt(form, attemptNumber) {{
        const startInput = getSlalomFormField(form, `attempt_${{attemptNumber}}_base_time_seconds`);
        const finishInput = getSlalomFormField(form, `attempt_${{attemptNumber}}_finish_time_seconds`);
        if (!(startInput instanceof HTMLInputElement) || !(finishInput instanceof HTMLInputElement)) {{
          return null;
        }}
        const startSeconds = parseHhmmssValue(startInput.value);
        const finishSeconds = parseHhmmssValue(finishInput.value);
        if (finishSeconds <= 0) {{
          return null;
        }}
        let penalties = 0;
        getSlalomFormFields(form, `attempt_${{attemptNumber}}_gate_`).forEach((field) => {{
          if (field instanceof HTMLInputElement) {{
            penalties += Number(field.value || 0);
          }}
        }});
        const distance = Math.max(0, finishSeconds - startSeconds);
        return {{
          attemptNumber,
          distance,
          total: distance + penalties,
        }};
      }}

      function recalcSlalomSheet() {{
        const forms = Array.from(document.querySelectorAll("form[action='/slalom/save']"))
          .filter((form) => form instanceof HTMLFormElement);
        const scored = [];
        forms.forEach((form) => {{
          const formId = form.id;
          const firstRow = document.querySelector(`[data-slalom-form="${{formId}}"][data-slalom-team]`);
          const resultNode = firstRow ? firstRow.querySelector("[data-slalom-result]") : null;
          const totalNode = firstRow ? firstRow.querySelector("[data-slalom-total]") : null;
          const placeNode = firstRow ? firstRow.querySelector("[data-slalom-place]") : null;
          const noCell = firstRow ? firstRow.querySelector("[data-slalom-no]") : null;
          const run1 = evaluateSlalomAttempt(form, 1);
          const run2 = evaluateSlalomAttempt(form, 2);
          const completedAttempts = [run1, run2].filter(Boolean).length;
          let best = null;
          if (run1 && run2) {{
            best = run1.total <= run2.total ? run1 : run2;
          }} else {{
            best = run1 || run2;
          }}
          if (resultNode instanceof HTMLElement) {{
            resultNode.textContent = best ? formatMmssValue(best.distance) : "";
          }}
          if (totalNode instanceof HTMLElement) {{
            totalNode.textContent = best ? formatMmssValue(best.total) : "";
          }}
          if (placeNode instanceof HTMLElement) {{
            placeNode.textContent = "";
          }}
          if (noCell instanceof HTMLElement) {{
            noCell.classList.remove("slalom-no-idle", "slalom-no-partial", "slalom-no-complete");
            if (completedAttempts >= 2) {{
              noCell.classList.add("slalom-no-complete");
            }} else if (completedAttempts === 1) {{
              noCell.classList.add("slalom-no-partial");
            }} else {{
              noCell.classList.add("slalom-no-idle");
            }}
          }}
          setSlalomAttemptBest(formId, 1, Boolean(best && best.attemptNumber === 1));
          setSlalomAttemptBest(formId, 2, Boolean(best && best.attemptNumber === 2));
          if (best && firstRow instanceof HTMLElement) {{
            scored.push({{
              formId,
              teamName: firstRow.getAttribute("data-slalom-team") || "",
              total: best.total,
            }});
          }}
        }});
        scored
          .sort((left, right) => left.total - right.total || left.teamName.localeCompare(right.teamName, "ru"))
          .forEach((item, index) => {{
                const firstRow = document.querySelector(`[data-slalom-form="${{item.formId}}"][data-slalom-team]`);
            const placeNode = firstRow ? firstRow.querySelector("[data-slalom-place]") : null;
            if (placeNode instanceof HTMLElement) {{
              placeNode.textContent = String(index + 1);
            }}
          }});
      }}

      function applySlalomAutoSave() {{
        document.querySelectorAll("form[action='/slalom/save']").forEach((form) => {{
          if (!(form instanceof HTMLFormElement) || form.dataset.autosaveBound === "1") {{
            return;
          }}
          document.querySelectorAll(`[form="${{form.id}}"]`).forEach((field) => {{
            if (!(field instanceof HTMLElement)) {{
              return;
            }}
            if (field instanceof HTMLInputElement) {{
              field.addEventListener("blur", () => {{
                recalcSlalomSheet();
                window.setTimeout(() => {{
                  if (form.contains(document.activeElement)) {{
                    return;
                  }}
                  submitSlalomForm(form);
                }}, 0);
              }});
            }}
          }});
          form.dataset.autosaveBound = "1";
        }});
      }}

      function applyStartOrderValidation() {{
        function runValidation(container) {{
          const inputs = Array.from(container.querySelectorAll("input.js-start-order"));
          if (!inputs.length) return;
          const form = inputs[0].closest("form");
          const hint = form ? form.querySelector(".order-conflict-hint") : null;
          const submitBtn = form ? (form.querySelector("button[type='submit']:not([name])") || form.querySelector("button[type='submit']")) : null;

          const counts = {{}};
          inputs.forEach((inp) => {{
            const v = (inp.value || "").trim();
            if (v && v !== "99") counts[v] = (counts[v] || 0) + 1;
          }});
          let hasDup = false;
          inputs.forEach((inp) => {{
            const v = (inp.value || "").trim();
            const dup = !!(v && v !== "99" && counts[v] > 1);
            inp.classList.toggle("order-conflict", dup);
            if (dup) hasDup = true;
          }});
          if (submitBtn) {{
            submitBtn.disabled = hasDup;
            submitBtn.title = hasDup ? "Устраните дублирующиеся номера старта" : "";
          }}
          if (hint) hint.classList.toggle("visible", hasDup);
        }}

        // bind on existing inputs
        document.querySelectorAll("input.js-start-order").forEach((inp) => {{
          inp.addEventListener("input", () => runValidation(inp.closest("form") || document));
        }});
        runValidation(document);
      }}

      document.addEventListener("input", (event) => {{
        if (event.target instanceof HTMLInputElement && event.target.hasAttribute("data-age-min")) {{
          validateMemberYears();
        }}
      }});
      validateMemberYears();
      applyTimeMasks();
      applySlalomPenaltyPickers();
      applySlalomAutoSave();
      applyStartOrderValidation();
      recalcSlalomSheet();
      window.addEventListener("load", () => {{
        if (!window.location.hash) {{
          return;
        }}
        const target = document.querySelector(window.location.hash);
        if (!target) {{
          return;
        }}
        setTimeout(() => {{
          target.scrollIntoView({{ behavior: "auto", block: "start" }});
        }}, 0);
      }});

      // saved=1 toast
      (function() {{
        const params = new URLSearchParams(window.location.search);
        if (params.get("saved") !== "1") return;
        const toast = document.createElement("div");
        toast.id = "save-toast";
        toast.textContent = "✓ Сохранено";
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add("save-toast-show"));
        setTimeout(() => {{
          toast.classList.remove("save-toast-show");
          setTimeout(() => toast.remove(), 400);
        }}, 2500);
        const url = new URL(window.location.href);
        url.searchParams.delete("saved");
        history.replaceState(null, "", url.toString());
      }})();
    </script>
  </body>
</html>
"""


def _status_label(status: str) -> str:
    return {
        "ok": "Готово",
        "warn": "Не завершено",
        "danger": "Требуется",
    }[status]


def _required_judge_card(title: str, prefix: str, judge: RequiredJudgeRecord) -> str:
    return f"""
<div class="judges-role-card">
  <span class="judges-role-tag">{escape(title)}</span>
  <div class="judge-field">
    <label for="{prefix}_last_name">Фамилия</label>
    <input id="{prefix}_last_name" name="{prefix}_last_name" value="{escape(judge.last_name)}" placeholder="Фамилия" />
  </div>
  <div class="judge-field">
    <label for="{prefix}_first_name">Имя</label>
    <input id="{prefix}_first_name" name="{prefix}_first_name" value="{escape(judge.first_name)}" placeholder="Имя" />
  </div>
  <div class="judge-field">
    <label for="{prefix}_patronymic">Отчество</label>
    <input id="{prefix}_patronymic" name="{prefix}_patronymic" value="{escape(judge.patronymic)}" placeholder="Отчество" />
  </div>
  <div class="judge-field">
    <label for="{prefix}_category">Категория</label>
    {_judge_category_select(f"{prefix}_category", judge.category)}
  </div>
</div>
"""


def _judge_card(index: int | str, judge: JudgeRecord) -> str:
    return f"""
<div class="judges-extra-row">
  <div class="judge-field">
    <label>Фамилия</label>
    <input name="judge_{index}_last_name" value="{escape(judge.last_name)}" placeholder="Фамилия" />
  </div>
  <div class="judge-field">
    <label>Имя</label>
    <input name="judge_{index}_first_name" value="{escape(judge.first_name)}" placeholder="Имя" />
  </div>
  <div class="judge-field">
    <label>Отчество</label>
    <input name="judge_{index}_patronymic" value="{escape(judge.patronymic)}" placeholder="Отчество" />
  </div>
  <div class="judge-field">
    <label>Категория</label>
    {_judge_category_select(f"judge_{index}_category", judge.category)}
  </div>
  <button type="button" class="judges-remove-btn" onclick="this.closest('.judges-extra-row').remove()">УБРАТЬ</button>
</div>
"""


def _judge_category_select(field_name: str, selected_value: str) -> str:
    options = "".join(
        f"<option value=\"{escape(value)}\" {'selected' if value == selected_value else ''}>{escape(value)}</option>"
        for value in [""] + JUDGE_CATEGORY_OPTIONS
    )
    return f"<select name=\"{escape(field_name)}\">{options}</select>"


def _required_judge_from_form(form_data: dict[str, str], prefix: str) -> RequiredJudgeRecord:
    return RequiredJudgeRecord(
        last_name=form_data.get(f"{prefix}_last_name", "").strip(),
        first_name=form_data.get(f"{prefix}_first_name", "").strip(),
        patronymic=form_data.get(f"{prefix}_patronymic", "").strip(),
        category=form_data.get(f"{prefix}_category", "").strip(),
    )


def _judges_from_form(form_data: dict[str, str]) -> list[JudgeRecord]:
    judge_indexes = sorted(
        {
            key.split("_")[1]
            for key in form_data
            if key.startswith("judge_") and key.endswith("_last_name")
        },
        key=int,
    )
    judges: list[JudgeRecord] = []
    for index in judge_indexes:
        judge = JudgeRecord(
            last_name=form_data.get(f"judge_{index}_last_name", "").strip(),
            first_name=form_data.get(f"judge_{index}_first_name", "").strip(),
            patronymic=form_data.get(f"judge_{index}_patronymic", "").strip(),
            category=form_data.get(f"judge_{index}_category", "").strip(),
        )
        if any([judge.last_name, judge.first_name, judge.patronymic, judge.category]):
            judges.append(judge)
    return judges


def _judge_full_name(judge: RequiredJudgeRecord) -> str:
    return " ".join(part for part in [judge.last_name, judge.first_name, judge.patronymic] if part)


def _judges_status(record: JudgesRecord) -> tuple[str, str]:
    required_complete = all(
        [
            record.chief_judge.is_complete,
            record.chief_secretary.is_complete,
            record.course_chief.is_complete,
        ]
    )
    if not required_complete:
        return ("danger", "Не заполнено")
    if not record.judges:
        return ("warn", "Только обязательные роли")
    return ("ok", "Состав заполнен")


def _first_category_link(base_path: str, db_name: str, settings: CompetitionSettingsRecord) -> str:
    if not settings.categories:
        return f"/settings?db={escape(db_name)}"
    return f"{base_path}?db={escape(db_name)}&category={escape(settings.categories[0].key)}"


def _has_any_sprint(db_path: Path, settings: CompetitionSettingsRecord) -> bool:
    return any(load_sprint_entries(db_path, category.key) for category in settings.categories)


def _has_any_parallel(db_path: Path, settings: CompetitionSettingsRecord) -> bool:
    return any(load_parallel_sprint_heats(db_path, category.key) for category in settings.categories)


def _has_any_slalom(db_path: Path, settings: CompetitionSettingsRecord) -> bool:
    return any(load_slalom_runs(db_path, category.key) for category in settings.categories)


def _has_any_long_race(db_path: Path, settings: CompetitionSettingsRecord) -> bool:
    return any(load_long_race_entries(db_path, category.key) for category in settings.categories)


def _category_label(category: Category) -> str:
    sex_label = {
        "men": "Мужчины",
        "women": "Женщины",
    }.get(category.normalized_sex, category.normalized_sex)
    age_label = {
        "U16": "U16",
        "U20": "U20",
        "U24": "U24",
        "Cup": "Кубок",
        "Veterans": "Ветераны",
    }.get(category.age_group, category.age_group)
    return f"{category.boat_class} {sex_label} {age_label}"


def create_app(data_dir: Path) -> WebApp:
    return WebApp(data_dir=data_dir)


def _normalize_filename(value: str) -> str:
    cleaned = value.strip().replace(" ", "_")
    return cleaned or "competition"


def _display_competition_name(db_name: str) -> str:
    if db_name.endswith(".db"):
        return db_name[:-3]
    return db_name

def _resolve_sprint_lineup(team: Team, stored_flags: dict[int, bool]) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for member_order, member in enumerate(team.crew_members, start=1):
        default_active = member.role != "reserve" and member_order <= _crew_main_count(team.boat_class)
        resolved.append(
            {
                "member_order": member_order,
                "member": member,
                "is_active": stored_flags.get(member_order, default_active),
            }
        )
    return resolved


def _sprint_lineup_cell(
    db_name: str,
    category_key: str,
    team: Team,
    lineup: list[dict[str, object]],
    is_open: bool,
    lineup_action_path: str = "/sprint/lineup",
) -> str:
    active_items = [item for item in lineup if bool(item["is_active"])]
    inactive_items = [item for item in lineup if not bool(item["is_active"])]
    required_count = _crew_main_count(team.boat_class)
    active_count = len(active_items)
    first_active_name = ""
    if active_items:
        first_member = active_items[0]["member"]
        if isinstance(first_member, TeamMember):
            first_active_name = first_member.full_name
    summary = escape(first_active_name or "Состав не выбран")
    if active_count > 1:
        summary += f" +{active_count - 1}"
    count_label = f"Состав {active_count}/{required_count}"
    warning = f'<span class="lineup-warning{" invalid-year" if active_count != required_count else ""}">{count_label}</span>'
    active_html = "".join(
        _sprint_lineup_member_control(db_name, category_key, team.name, item, "убрать", False, lineup_action_path)
        for item in active_items
    ) or '<li class="subtle">Пусто</li>'
    inactive_html = "".join(
        _sprint_lineup_member_control(db_name, category_key, team.name, item, "вернуть", True, lineup_action_path)
        for item in inactive_items
    ) or '<li class="subtle">Пусто</li>'
    return f"""
<details class="lineup-details"{" open" if is_open else ""}>
  <summary><span class="lineup-summary">{warning}<span class="lineup-names">{summary}</span></span></summary>
  <div class="lineup-groups">
    <div>
      <strong>В старте</strong>
      <ul class="compact-list lineup-list">{active_html}</ul>
    </div>
    <div>
      <strong>Вне старта</strong>
      <ul class="compact-list lineup-list">{inactive_html}</ul>
    </div>
  </div>
</details>
"""


def _sprint_lineup_member_control(
    db_name: str,
    category_key: str,
    team_name: str,
    lineup_item: dict[str, object],
    label: str,
    make_active: bool,
    lineup_action_path: str,
) -> str:
    member = lineup_item["member"]
    member_order = int(lineup_item["member_order"])
    if not isinstance(member, TeamMember):
        return ""
    return f"""
<li>
  <span class="lineup-member-name">{escape(member.full_name or 'Не заполнено')}</span>
  <button
    type="submit"
    class="link-button"
    formaction="{escape(lineup_action_path)}"
    name="lineup_target"
    value="{escape(team_name)}|{member_order}|{1 if make_active else 0}"
  >{escape(label)}</button>
</li>
"""


def _sprint_table_row(
    index: int,
    db_name: str,
    category_key: str,
    team: Team,
    entry: SprintEntry | None,
    place: int | None,
    lineup: list[dict[str, object]],
    is_open: bool,
) -> str:
    status_value = entry.status if entry else "OK"
    place_value = place if place is not None else ""
    crew = _sprint_lineup_cell(db_name, category_key, team, lineup, is_open)
    return f"""
<tr id="slalom-team-{team.start_number}">
  <td class="col-pp">
    <input type="hidden" name="row_{index}_team_name" value="{escape(team.name)}" />
    <input class="js-start-order" inputmode="numeric" name="row_{index}_start_order" value="{entry.start_order if entry else index}" />
  </td>
  <td class="col-time"><input class="inline-time" data-time-mask="mmss" name="row_{index}_start_time" value="{escape(entry.start_time if entry else '')}" placeholder="10:00" /></td>
  <td>{escape(team.name)}</td>
  <td class="col-number">{team.start_number}</td>
  <td class="crew-cell">{crew}</td>
  <td>{escape(team.region)}</td>
  <td class="col-time"><input class="inline-time" data-time-mask="mmss" name="row_{index}_base_time_seconds" value="{_format_mmss(entry.base_time_seconds if entry else 0)}" placeholder="01:23" /></td>
  <td class="col-time"><input class="inline-time" data-time-mask="mmss" name="row_{index}_behavior_penalty_seconds" value="{_format_mmss(entry.behavior_penalty_seconds if entry else 0)}" placeholder="00:00" /></td>
  <td class="col-place">{place_value}</td>
  <td class="col-status">{_sprint_status_select(f"row_{index}_status", status_value)}</td>
</tr>
"""


def _long_race_table_row(
    index: int,
    db_name: str,
    category_key: str,
    team: Team,
    entry: SprintEntry | None,
    place: int | None,
    lineup: list[dict[str, object]],
    is_open: bool,
) -> str:
    status_value = entry.status if entry else "OK"
    place_value = place if place is not None else ""
    is_non_participant = bool(entry and entry.start_order == 99)
    disabled_attr = ' disabled="disabled"' if is_non_participant else ""
    crew = _sprint_lineup_cell(
        db_name,
        category_key,
        team,
        lineup,
        is_open,
        "/long-race/lineup",
    )
    return f"""
<tr>
  <td class="col-pp">
    <input type="hidden" name="row_{index}_team_name" value="{escape(team.name)}" />
    {_long_race_group_select(f"row_{index}_start_order", entry.start_order if entry else 1)}
  </td>
  <td class="col-time"><input class="inline-time long-race-dependent" data-time-mask="mmss" name="row_{index}_start_time" value="{escape(entry.start_time if entry else '')}" placeholder="10:00"{disabled_attr} /></td>
  <td>{escape(team.name)}</td>
  <td class="col-number">{team.start_number}</td>
  <td class="crew-cell">{crew}</td>
  <td>{escape(team.region)}</td>
  <td class="col-time"><input class="inline-time long-race-dependent" data-time-mask="mmss" name="row_{index}_base_time_seconds" value="{_format_mmss(entry.base_time_seconds if entry else 0)}" placeholder="30:00"{disabled_attr} /></td>
  <td class="col-time"><input class="inline-time long-race-dependent" data-time-mask="mmss" name="row_{index}_behavior_penalty_seconds" value="{_format_mmss(entry.behavior_penalty_seconds if entry else 0)}" placeholder="00:00"{disabled_attr} /></td>
  <td class="col-place">{place_value}</td>
  <td class="col-status">{_sprint_status_select(f"row_{index}_status", status_value, is_non_participant, "long-race-dependent")}</td>
</tr>
"""


def _parallel_sprint_start_node_html(
    index: int,
    db_name: str,
    category_key: str,
    team: Team,
    entry: SprintEntry | None,
    is_open: bool,
) -> str:
    lineup_href = f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}&open_team={quote(team.name)}#parallel-lineup"
    return f"""
<article class="h2h-start-node">
  <div class="h2h-start-node-time">
    <label class="subtle">Время старта</label>
    <input type="hidden" name="row_{index}_team_name" value="{escape(team.name)}" />
    <input type="hidden" name="row_{index}_start_order" value="{entry.start_order if entry else index}" />
    <input class="inline-time" data-time-mask="hhmm" name="row_{index}_start_time" value="{escape(entry.start_time if entry else '')}" placeholder="10:00" />
  </div>
  <div class="h2h-start-node-main">
    <div class="h2h-start-node-top">
      <div class="h2h-start-node-number">
        <span class="sr-only">№ команды</span>
        № {team.start_number}
      </div>
      <div class="h2h-start-node-name">
        <span class="sr-only">Команда</span>
        <a href="{lineup_href}">{escape(team.name)}</a>
      </div>
    </div>
    <div class="h2h-start-node-bottom">
      <a class="subtle" href="{lineup_href}">Состав</a>
    </div>
  </div>
</article>
"""


def _parallel_sprint_lineup_panel_html(
    db_name: str,
    category_key: str,
    team: Team,
    lineup: list[dict[str, object]],
) -> str:
    active_items = [item for item in lineup if bool(item["is_active"])]
    inactive_items = [item for item in lineup if not bool(item["is_active"])]
    active_html = "".join(
        _sprint_lineup_member_control(db_name, category_key, team.name, item, "убрать", False, "/parallel-sprint/lineup")
        for item in active_items
    ) or '<li class="subtle">Пусто</li>'
    inactive_html = "".join(
        _sprint_lineup_member_control(db_name, category_key, team.name, item, "вернуть", True, "/parallel-sprint/lineup")
        for item in inactive_items
    ) or '<li class="subtle">Пусто</li>'
    return f"""
  <section id="parallel-lineup" class="panel-card parallel-lineup-panel">
    <div class="section-head">
      <div>
        <h2>Состав команды</h2>
        <p class="subtle">{escape(team.name)} · № {team.start_number}</p>
      </div>
      <a class="secondary-link" href="/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}">Скрыть</a>
    </div>
    <div class="parallel-lineup-grid">
      <div>
        <strong>В старте</strong>
        <ul class="compact-list lineup-list">{active_html}</ul>
      </div>
      <div>
        <strong>Вне старта</strong>
        <ul class="compact-list lineup-list">{inactive_html}</ul>
      </div>
    </div>
  </section>
"""


def _parallel_sprint_rules_hint(team_count: int) -> str:
    if team_count <= 1:
        return "Сетка H2H формируется по результатам спринта. Пока в категории меньше двух команд, строить сетку еще рано."
    if team_count == 2:
        return "Сетка H2H формируется по результатам спринта. При двух командах сразу проводится один финальный заезд."
    if team_count == 3:
        return "Сетка H2H формируется по результатам спринта. При трех командах второй этап рассчитан на 2 команды, а еще две команды проводят один заезд первого этапа."
    if 4 <= team_count <= 7:
        return "Сетка H2H формируется по результатам спринта. При 4-7 командах второй этап рассчитан на 4 команды, остальные сначала проходят первый этап."
    if 8 <= team_count <= 15:
        return "Сетка H2H формируется по результатам спринта. При 8-15 командах второй этап рассчитан на 8 команд, остальные сначала проходят первый этап."
    if 16 <= team_count <= 31:
        return "Сетка H2H формируется по результатам спринта. При 16-31 командах второй этап рассчитан на 16 команд, остальные сначала проходят первый этап."
    return "Сетка H2H формируется по результатам спринта. Если число команд равно 4, 8, 16 или 32, первый этап не нужен и команды сразу попадают во второй этап."


def _parallel_penalties_from_pattern(pattern: str) -> tuple[int, int]:
    values = pattern.split("/", 1)
    if len(values) != 2:
        return (0, 0)
    try:
        return (int(values[0]), int(values[1]))
    except ValueError:
        return (0, 0)


def _parallel_buoy_pattern(left_penalty_seconds: int, right_penalty_seconds: int) -> str:
    allowed = {"0/0", "50/0", "0/50", "50/50"}
    value = f"{left_penalty_seconds}/{right_penalty_seconds}"
    return value if value in allowed else "0/0"


def _parallel_buoy_pattern_options(current: str) -> str:
    options = ["0/0", "50/0", "0/50", "50/50"]
    return "".join(
        f'<option value="{value}" {"selected" if value == current else ""}>{value}</option>'
        for value in options
    )


def _parallel_sprint_preview_columns_html(
    db_name: str,
    category_key: str,
    ordered_teams: list[Team],
    saved_by_team: dict[str, SprintEntry],
    sprint_order: list[str],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    team_map: dict[str, Team],
    open_result_round_title: str,
    open_result_panel: str,
) -> str:
    if len(ordered_teams) < 2:
        return ""
    specs = _parallel_sprint_match_specs([team.name for team in ordered_teams])
    if not specs:
        return ""
    grouped: dict[str, list[dict[str, object]]] = {}
    order = _parallel_round_titles_in_display_order(specs)
    for spec in specs:
        grouped.setdefault(str(spec["round_title"]), []).append(spec)

    visible_titles: list[str] = []
    last_competitive_title = ""
    for title in order:
        if not visible_titles:
            visible_titles.append(title)
            if title not in {"Финал A", "Финал B"}:
                last_competitive_title = title
            continue
        if title in {"Финал A", "Финал B"}:
            if _parallel_round_complete(grouped.get("1/2 финала", []), heat_meta, saved_by_round):
                visible_titles.append(title)
            continue
        if last_competitive_title and _parallel_round_complete(grouped.get(last_competitive_title, []), heat_meta, saved_by_round):
            visible_titles.append(title)
            last_competitive_title = title
        else:
            break

    columns: list[str] = []
    for title in visible_titles:
        round_specs = grouped.get(title, [])
        clear_button = f"""
  <form method="post" action="/parallel-sprint/clear-stage" onsubmit="return confirm('Очистить этап {escape(title)} и все следующие?');">
    <input type="hidden" name="db" value="{escape(db_name)}" />
    <input type="hidden" name="category_key" value="{escape(category_key)}" />
    <input type="hidden" name="stage_title" value="{escape(title)}" />
    <button type="submit" class="secondary-link danger-link">Очистить этап</button>
  </form>
"""
        cards = "".join(
            _parallel_sprint_preview_heat_card_html(
                db_name,
                category_key,
                spec,
                heat_meta,
                saved_by_round,
                team_map,
            )
            for spec in round_specs
        )
        columns.append(
            f"""
<section id="{_parallel_round_anchor_id(title)}" class="h2h-column">
  <div class="section-head compact-head">
    <h2>{escape(title)}</h2>
    {clear_button}
  </div>
  <div class="h2h-column-body">{cards}</div>
  {open_result_panel if open_result_round_title == title else ""}
</section>
"""
        )
    return "".join(columns)


def _parallel_sprint_preview_stage_one_pairs(ordered_teams: list[Team]) -> list[tuple[Team, Team]]:
    team_count = len(ordered_teams)
    bracket_size = 8 if team_count <= 15 else 16
    extra_count = max(0, team_count - bracket_size)
    if extra_count <= 0:
        return []
    stage_team_count = min(team_count, max(2, 2 * ((extra_count + 1) // 2)))
    stage_teams = ordered_teams[-stage_team_count:]
    half = len(stage_teams) // 2
    lower = stage_teams[:half]
    upper = stage_teams[half:]
    return list(zip(reversed(upper), lower, strict=True))


def _parallel_sprint_display_stage_one_specs(ordered_teams: list[Team]) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for index, (left_team, right_team) in enumerate(_parallel_sprint_preview_stage_one_pairs(ordered_teams), start=1):
        specs.append(
            {
                "round_name": f"display_stage1_{index}",
                "round_title": "Первый этап",
                "match_index": index,
                "left_source": ("team", (left_team.name, left_team.start_number)),
                "right_source": ("team", (right_team.name, right_team.start_number)),
            }
        )
    return specs


def _parallel_sprint_display_second_stage_specs(
    first_stage_specs: list[dict[str, object]],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    heat_meta: dict[str, ParallelSprintHeatMeta],
) -> list[dict[str, object]]:
    if len(first_stage_specs) < 2:
        return []
    completed_rounds: list[str] = []
    for spec in first_stage_specs:
        round_name = str(spec["round_name"])
        if round_name not in saved_by_round or round_name not in heat_meta:
            return []
        left_saved, right_saved = saved_by_round[round_name]
        if PARALLEL_PENDING_TOTAL_SECONDS in {left_saved.total_time_seconds, right_saved.total_time_seconds}:
            return []
        if not heat_meta[round_name].winner_team_name:
            return []
        completed_rounds.append(round_name)
    winner_specs: list[dict[str, object]] = []
    loser_specs: list[dict[str, object]] = []
    for index in range(0, len(completed_rounds), 2):
        pair = completed_rounds[index:index + 2]
        if len(pair) < 2:
            break
        winner_specs.append(
            {
                "round_name": f"display_stage2_winners_{len(winner_specs) + 1}",
                "round_title": "2й этап",
                "match_index": len(winner_specs) + 1,
                "left_source": ("winner", pair[0]),
                "right_source": ("winner", pair[1]),
            }
        )
        loser_specs.append(
            {
                "round_name": f"display_stage2_losers_{len(loser_specs) + 1}",
                "round_title": "2й этап",
                "match_index": len(winner_specs) + len(loser_specs) + 1,
                "left_source": ("loser", pair[0]),
                "right_source": ("loser", pair[1]),
            }
        )
    return winner_specs + loser_specs


def _parallel_round_titles_in_display_order(specs: list[dict[str, object]]) -> list[str]:
    titles: list[str] = []
    for spec in specs:
        title = str(spec["round_title"])
        if title not in titles:
            titles.append(title)
    if "Финал B" in titles and "Финал A" in titles:
        titles = [title for title in titles if title not in {"Финал A", "Финал B"}] + ["Финал A", "Финал B"]
    return titles


def _parallel_round_names_from_title_and_later(
    grouped: dict[str, list[dict[str, object]]],
    order: list[str],
    start_title: str,
) -> list[str]:
    if start_title not in order:
        return []
    result: list[str] = []
    for title in order[order.index(start_title):]:
        result.extend(str(spec["round_name"]) for spec in grouped.get(title, []))
    return result


def _parallel_round_anchor_id(title: str) -> str:
    mapping = {
        "Первый этап": "h2h-stage-1",
        "1/16 финала": "h2h-round-16",
        "1/8 финала": "h2h-round-8",
        "1/4 финала": "h2h-quarterfinal",
        "1/2 финала": "h2h-semifinal",
        "Финал A": "h2h-final-a",
        "Финал B": "h2h-final-b",
    }
    return mapping.get(title, "h2h-round")


def _parallel_round_complete(
    round_specs: list[dict[str, object]],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> bool:
    if not round_specs:
        return False
    for spec in round_specs:
        round_name = str(spec["round_name"])
        if round_name not in saved_by_round or round_name not in heat_meta:
            return False
        left_saved, right_saved = saved_by_round[round_name]
        if PARALLEL_PENDING_TOTAL_SECONDS in {left_saved.total_time_seconds, right_saved.total_time_seconds}:
            return False
        if not heat_meta[round_name].winner_team_name:
            return False
    return True


def _parallel_sprint_standings_panel_html(
    ordered_teams: list[Team],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> str:
    final_a = saved_by_round.get("final_a")
    final_b = saved_by_round.get("final_b")
    if not final_a or not final_b:
        return ""
    if PARALLEL_PENDING_TOTAL_SECONDS in {
        final_a[0].total_time_seconds,
        final_a[1].total_time_seconds,
        final_b[0].total_time_seconds,
        final_b[1].total_time_seconds,
    }:
        return ""
    ordered_names = _parallel_sprint_ordered_names(ordered_teams, saved_by_round)

    team_map = {team.name: team for team in ordered_teams}
    cards = "".join(
        _parallel_sprint_standing_card_html(index, team_map.get(team_name))
        for index, team_name in enumerate(ordered_names, start=1)
    )
    return f"""
<section id="h2h-standings" class="h2h-column">
  <div class="section-head compact-head">
    <h2>Итоговые места H2H</h2>
  </div>
  <div class="h2h-column-body">{cards}</div>
</section>
"""


def _parallel_sprint_standing_card_html(place: int, team: Team | None) -> str:
    team_name = team.name if team is not None else ""
    region = team.region if team is not None else ""
    points = points_for_place("parallel_sprint", place)
    return f"""
<article class="h2h-heat-card preview">
  <div class="h2h-heat-grid">
    <div class="h2h-row preview">
      <div class="h2h-no-cell">{place}</div>
      <div class="h2h-main-cell">
        <div class="h2h-team-name">{escape(team_name)}</div>
        <div class="h2h-region">{escape(region)}</div>
      </div>
      <div class="h2h-time-cell">
        <div class="h2h-time-total">{points}</div>
      </div>
    </div>
  </div>
</article>
"""


def _parallel_sprint_ordered_names(
    ordered_teams: list[Team],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> list[str]:
    final_a = saved_by_round.get("final_a")
    final_b = saved_by_round.get("final_b")
    if not final_a or not final_b:
        return [team.name for team in ordered_teams]
    if PARALLEL_PENDING_TOTAL_SECONDS in {
        final_a[0].total_time_seconds,
        final_a[1].total_time_seconds,
        final_b[0].total_time_seconds,
        final_b[1].total_time_seconds,
    }:
        return [team.name for team in ordered_teams]

    places = resolve_four_team_places(final_a, final_b)
    ordered_names: list[str] = [team_name for team_name, _place in sorted(places.items(), key=lambda item: item[1])]
    used_names = set(ordered_names)

    grouped_heats: dict[str, list[tuple[str, ParallelSprintHeatResult, ParallelSprintHeatResult]]] = {}
    for round_name, left, right in (
        (round_name, left, right) for round_name, (left, right) in saved_by_round.items()
    ):
        title = _parallel_round_title_from_name(round_name)
        grouped_heats.setdefault(title, []).append((round_name, left, right))

    title_order = ["1/16 финала", "1/8 финала", "1/4 финала", "Первый этап"]
    for title in title_order:
        heats = grouped_heats.get(title, [])
        if not heats:
            continue
        losers: list[ParallelSprintHeatResult] = []
        for _round_name, left, right in heats:
            if PARALLEL_PENDING_TOTAL_SECONDS in {left.total_time_seconds, right.total_time_seconds}:
                continue
            winner = resolve_heat_winner(left, right)
            loser = right if winner.team_name == left.team_name else left
            losers.append(loser)
        ordered_names.extend(entry.team_name for entry in rank_eliminated_crews(losers) if entry.team_name not in used_names)
        used_names = set(ordered_names)

    for team in ordered_teams:
        if team.name not in used_names:
            ordered_names.append(team.name)
            used_names.add(team.name)
    return ordered_names


def _parallel_sprint_full_places_map(
    ordered_teams: list[Team],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> dict[str, int]:
    ordered_names = _parallel_sprint_ordered_names(ordered_teams, saved_by_round)
    return {
        team_name: index
        for index, team_name in enumerate(ordered_names, start=1)
    }


def _parallel_sprint_last_result_data(
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    heat_meta: dict[str, ParallelSprintHeatMeta],
) -> dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatMeta | None, str]]:
    round_rank = {
        "Первый этап": 1,
        "1/16 финала": 2,
        "1/8 финала": 3,
        "1/4 финала": 4,
        "1/2 финала": 5,
        "Финал B": 6,
        "Финал A": 7,
    }
    result_by_team: dict[str, tuple[int, ParallelSprintHeatResult, ParallelSprintHeatMeta | None, str]] = {}
    for round_name, (left, right) in saved_by_round.items():
        title = _parallel_round_title_from_name(round_name)
        rank = round_rank.get(title, 0)
        meta = heat_meta.get(round_name)
        for lane, entry in (("left", left), ("right", right)):
            if not entry.team_name or entry.total_time_seconds >= PARALLEL_PENDING_TOTAL_SECONDS:
                continue
            current = result_by_team.get(entry.team_name)
            if current is None or rank >= current[0]:
                result_by_team[entry.team_name] = (rank, entry, meta, lane)
    return {
        team_name: (entry, meta, lane)
        for team_name, (_rank, entry, meta, lane) in result_by_team.items()
    }


def _parallel_round_title_from_name(round_name: str) -> str:
    if round_name.startswith("stage1_seed_"):
        return "Первый этап"
    if round_name.startswith("quarterfinal_"):
        return "1/4 финала"
    if round_name.startswith("eighthfinal_"):
        return "1/8 финала"
    if round_name.startswith("sixteenthfinal_"):
        return "1/16 финала"
    if round_name.startswith("semifinal_"):
        return "1/2 финала"
    if round_name == "final_a":
        return "Финал A"
    if round_name == "final_b":
        return "Финал B"
    return round_name


def _parallel_sprint_result_panel_html(
    db_name: str,
    category_key: str,
    sprint_order: list[str],
    open_result: str,
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    team_map: dict[str, Team],
    start_entries_by_team: dict[str, SprintEntry],
) -> str:
    if not open_result:
        return ""
    round_name, lane = _parse_parallel_result_target(open_result)
    if not round_name or lane not in {"left", "right"}:
        return ""
    spec = next((spec for spec in _parallel_sprint_match_specs(sprint_order) if str(spec["round_name"]) == round_name), None)
    if spec is None:
        return ""
    participants = _parallel_resolved_heat_participants(spec, heat_meta, saved_by_round)
    target_name = participants["left_name"] if lane == "left" else participants["right_name"]
    team = team_map.get(target_name)
    if team is None:
        return ""
    meta = heat_meta.get(round_name)
    saved_heat = saved_by_round.get(round_name)
    if lane == "left":
        base_time_seconds = meta.left_base_time_seconds if meta else 0
        penalties = _parallel_buoy_penalties(meta.left_penalty_seconds if meta else 0)
        other_name = participants["right_name"]
        other_seed = participants["right_seed"]
    else:
        base_time_seconds = meta.right_base_time_seconds if meta else 0
        penalties = _parallel_buoy_penalties(meta.right_penalty_seconds if meta else 0)
        other_name = participants["left_name"]
        other_seed = participants["left_seed"]
    total = base_time_seconds + penalties[0] + penalties[1]
    team_seed = participants["left_seed"] if lane == "left" else participants["right_seed"]
    return f"""
  <section id="parallel-result" class="panel-card parallel-result-panel">
    <div class="section-head">
      <div>
        <h2>Результат заезда</h2>
        <p class="subtle">{escape(team.name)} · {escape(str(spec["round_title"]))} · заезд {spec["match_index"]}</p>
      </div>
      <a class="secondary-link" href="/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}">Скрыть</a>
    </div>
    <form method="post" action="/parallel-sprint/result" class="team-form-grid">
      <input type="hidden" name="db" value="{escape(db_name)}" />
      <input type="hidden" name="category_key" value="{escape(category_key)}" />
      <input type="hidden" name="round_name" value="{escape(round_name)}" />
      <input type="hidden" name="lane" value="{escape(lane)}" />
      <input type="hidden" name="team_name" value="{escape(team.name)}" />
      <input type="hidden" name="team_start_order" value="{team_seed}" />
      <input type="hidden" name="other_team_name" value="{escape(other_name)}" />
      <input type="hidden" name="other_start_order" value="{other_seed}" />
      <label>Время <input class="inline-time" data-time-mask="mmss" name="base_time_seconds" value="{_format_mmss(base_time_seconds)}" placeholder="00:00" /></label>
      <label>1й буй {_parallel_buoy_select("buoy_one", penalties[0])}</label>
      <label>2й буй {_parallel_buoy_select("buoy_two", penalties[1])}</label>
      <label>Итог <input value="{_format_mmss(total)}" readonly="readonly" /></label>
      <button type="submit">Сохранить результат</button>
    </form>
</section>
"""


def _parallel_sprint_open_result_round_title(
    sprint_order: list[str],
    open_result: str,
) -> str:
    if not open_result:
        return ""
    round_name, lane = _parse_parallel_result_target(open_result)
    if not round_name or lane not in {"left", "right"}:
        return ""
    spec = next((spec for spec in _parallel_sprint_match_specs(sprint_order) if str(spec["round_name"]) == round_name), None)
    if spec is None:
        return ""
    return str(spec["round_title"])


def _parse_parallel_result_target(value: str) -> tuple[str, str]:
    round_name, separator, lane = value.partition("|")
    if not separator:
        return ("", "")
    return (round_name.strip(), lane.strip())


def _parallel_buoy_penalties(total_penalty_seconds: int) -> tuple[int, int]:
    if total_penalty_seconds <= 0:
        return (0, 0)
    if total_penalty_seconds == 50:
        return (50, 0)
    return (50, 50)


def _parallel_buoy_select(field_name: str, current: int) -> str:
    options = "".join(
        f'<option value="{value}" {"selected" if value == current else ""}>{value}</option>'
        for value in (0, 50)
    )
    return f'<select name="{field_name}">{options}</select>'


def _parallel_display_total(total_time_seconds: int) -> str:
    if total_time_seconds >= PARALLEL_PENDING_TOTAL_SECONDS:
        return ""
    return _format_mmss(total_time_seconds)


def _parallel_sprint_preview_heat_card_html(
    db_name: str,
    category_key: str,
    spec: dict[str, object],
    heat_meta: dict[str, ParallelSprintHeatMeta],
    saved_by_round: dict[str, tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
    team_map: dict[str, Team],
) -> str:
    round_name = str(spec["round_name"])
    round_title = str(spec["round_title"])
    participants = _parallel_resolved_heat_participants(spec, heat_meta, saved_by_round)
    left_name = participants["left_name"]
    right_name = participants["right_name"]
    left_team = team_map.get(left_name)
    right_team = team_map.get(right_name)
    left_total = ""
    right_total = ""
    left_is_winner = False
    right_is_winner = False
    left_is_loser = False
    right_is_loser = False
    if round_name in saved_by_round:
        left_saved, right_saved = saved_by_round[round_name]
        left_total = _parallel_display_total(left_saved.total_time_seconds)
        right_total = _parallel_display_total(right_saved.total_time_seconds)
        if PARALLEL_PENDING_TOTAL_SECONDS not in {left_saved.total_time_seconds, right_saved.total_time_seconds}:
            winner = resolve_heat_winner(left_saved, right_saved)
            if winner.team_name == left_saved.team_name:
                left_is_winner = True
                right_is_loser = True
            elif winner.team_name == right_saved.team_name:
                right_is_winner = True
                left_is_loser = True
    return f"""
<article class="h2h-heat-card preview">
  <div class="h2h-heat-grid">
    {_parallel_sprint_preview_row_html(db_name, category_key, round_name, round_title, 'left', left_team, left_total, left_is_winner, left_is_loser)}
    {_parallel_sprint_preview_row_html(db_name, category_key, round_name, round_title, 'right', right_team, right_total, right_is_winner, right_is_loser)}
  </div>
</article>
"""


def _parallel_sprint_preview_row_html(
    db_name: str,
    category_key: str,
    round_name: str,
    round_title: str,
    lane: str,
    team: Team | None,
    total_time: str,
    is_winner: bool,
    is_loser: bool,
) -> str:
    team_name = team.name if team is not None else "Ожидание результата"
    team_number = f"№ {team.start_number}" if team is not None else "№ -"
    region = team.region if team is not None else ""
    row_class = "h2h-row preview"
    if is_winner:
        row_class += " winner"
    if is_loser:
        row_class += " loser"
    result_link = (
        f"/parallel-sprint?db={quote(db_name)}&category={quote(category_key)}&open_result={quote(round_name + '|' + lane)}#{_parallel_round_anchor_id(round_title)}"
        if team is not None
        else "#"
    )
    main_cell_inner = f"""
  <div class="h2h-team-name">{escape(team_name)}</div>
  <div class="h2h-region">{escape(region)}</div>
"""
    main_cell = (
        f'<a class="h2h-main-cell h2h-main-link" href="{result_link}">{main_cell_inner}</a>'
        if team is not None
        else f'<div class="h2h-main-cell">{main_cell_inner}</div>'
    )
    return f"""
<div class="{row_class}">
  <div class="h2h-no-cell">{team_number}</div>
  {main_cell}
  <div class="h2h-time-cell">
    <div class="h2h-time-total">{escape(total_time or "00:00")}</div>
  </div>
</div>
"""




def _sprint_results_protocol_row(
    team: Team,
    entry: SprintEntry | None,
    place: int | None,
    lineup: list[dict[str, object]],
) -> str:
    lineup_text = "<br />".join(_active_lineup_labels(lineup)) or "Состав не определен"
    start_time = entry.start_time if entry else ""
    base_time = _format_mmss(entry.base_time_seconds) if entry else ""
    penalty = _format_mmss(entry.behavior_penalty_seconds) if entry else ""
    points = points_for_place("sprint", place) if place else 0
    place_text = str(place) if place else ""
    start_order_text = str(entry.start_order) if entry and entry.start_order else ""
    return f"""
<tr>
  <td class="col-pp">{start_order_text}</td>
  <td class="col-number">{team.start_number}</td>
  <td>{escape(team.name)}</td>
  <td class="crew-cell protocol-crew">{lineup_text}</td>
  <td>{escape(team.region)}</td>
  <td class="col-time">{escape(start_time)}</td>
  <td class="col-time">{escape(base_time)}</td>
  <td class="col-time">{escape(penalty)}</td>
  <td class="col-place">{place_text}</td>
  <td class="col-place">{points}</td>
</tr>
"""


def _long_race_results_protocol_row(
    team: Team,
    entry: SprintEntry | None,
    place: int | None,
    lineup: list[dict[str, object]],
) -> str:
    lineup_text = "<br />".join(_active_lineup_labels(lineup)) or "Состав не определен"
    start_time = entry.start_time if entry else ""
    base_time = _format_mmss(entry.base_time_seconds) if entry else ""
    penalty = _format_mmss(entry.behavior_penalty_seconds) if entry else ""
    points = _long_race_points_for_entry(entry, place)
    place_text = str(place) if place else ""
    start_order_text = "н/у" if entry and entry.start_order == 99 else (str(entry.start_order) if entry and entry.start_order else "")
    return f"""
<tr>
  <td class="col-pp">{start_order_text}</td>
  <td class="col-number">{team.start_number}</td>
  <td>{escape(team.name)}</td>
  <td class="crew-cell protocol-crew">{lineup_text}</td>
  <td>{escape(team.region)}</td>
  <td class="col-time">{escape(start_time)}</td>
  <td class="col-time">{escape(base_time)}</td>
  <td class="col-time">{escape(penalty)}</td>
  <td class="col-place">{place_text}</td>
  <td class="col-place">{points}</td>
</tr>
"""


def _slalom_results_protocol_row(
    team: Team,
    runs: list[object],
    place: int | None,
    lineup: list[dict[str, object]],
    scored_runs: list[SlalomRun],
    gate_count: int,
) -> str:
    lineup_text = "<br />".join(_active_slalom_protocol_labels(lineup)) or "Состав не определен"
    run_by_attempt = {getattr(run, "attempt_number", 0): run for run in runs}
    scored_by_attempt = {run.attempt_number: run for run in scored_runs}
    best_run = best_run_for_team(scored_runs) if scored_runs else None
    place_text = str(place) if place else ""
    attempt_rows = []
    for attempt_number in (1, 2):
        raw_run = run_by_attempt.get(attempt_number)
        scored_run = scored_by_attempt.get(attempt_number)
        is_best = best_run is not None and best_run.attempt_number == attempt_number
        attempt_label = f"{attempt_number}я попытка"
        if is_best:
            attempt_label += ' <span class="slalom-best-attempt-note">лучшая</span>'
        start_text = ""
        finish_text = ""
        total_text = ""
        if raw_run is not None:
            base_time_seconds = int(getattr(raw_run, "base_time_seconds", 0))
            finish_time_seconds = int(getattr(raw_run, "finish_time_seconds", 0))
            if base_time_seconds > 0:
                start_text = _format_hhmmss(base_time_seconds)
            if finish_time_seconds > 0:
                finish_text = _format_hhmmss(finish_time_seconds)
        if scored_run is not None:
            total_text = _format_mmss(scored_run.total_time_seconds)
        gate_penalties = list(getattr(raw_run, "gate_penalties", [])) if raw_run is not None else []
        if len(gate_penalties) < gate_count:
            gate_penalties += [0] * (gate_count - len(gate_penalties))
        gate_cells = "".join(
            f'<td class="slalom-gate-value">{value}</td>'
            for value in gate_penalties[:gate_count]
        )
        attempt_rows.append(
            f"""
<tr class="slalom-protocol-attempt slalom-protocol-attempt-{attempt_number}{' best' if is_best else ''}">
  {'<td rowspan="2" class="col-number">' + str(team.start_number) + '</td>' if attempt_number == 1 else ''}
  {'<td rowspan="2">' + escape(team.name) + '</td>' if attempt_number == 1 else ''}
  {'<td rowspan="2" class="protocol-slalom-subject">' + escape(team.region) + '</td>' if attempt_number == 1 else ''}
  {'<td rowspan="2" class="crew-cell protocol-crew">' + lineup_text + '</td>' if attempt_number == 1 else ''}
  <td class="slalom-attempt-name">{attempt_label}</td>
  <td class="col-time">{escape(start_text)}</td>
  <td class="col-time">{escape(finish_text)}</td>
  {gate_cells}
  <td class="col-time">{escape(total_text)}</td>
  {'<td rowspan="2" class="col-place">' + place_text + '</td>' if attempt_number == 1 else ''}
</tr>
"""
        )
    return "".join(attempt_rows)


def _slalom_team_sheet_rows_html(
    db_name: str,
    category_key: str,
    form_id: str,
    team: Team,
    gate_count: int,
    team_runs: list[object],
    scored_runs: list[SlalomRun],
    place: int | None,
    is_open: bool,
) -> str:
    run_by_attempt = {getattr(run, "attempt_number", 0): run for run in team_runs}
    place_run = None
    best_attempt_number = 0
    if scored_runs:
        place_run = best_run_for_team(scored_runs)
        best_attempt_number = place_run.attempt_number
    completed_attempts = len({run.attempt_number for run in scored_runs})
    no_status_class = " slalom-no-idle"
    if completed_attempts >= 2:
        no_status_class = " slalom-no-complete"
    elif completed_attempts == 1:
        no_status_class = " slalom-no-partial"
    place_text = str(place) if place else ""
    result_text = _format_mmss(place_run.distance_time_seconds) if place_run is not None else ""
    total_text = _format_mmss(place_run.total_time_seconds) if place_run is not None else ""
    lineup_href = f"/slalom?db={quote(db_name)}&category={quote(category_key)}&open_team={quote(team.name)}#slalom-lineup"
    gate_headers = "".join(f'<th class="slalom-gate">{gate_index}в</th>' for gate_index in range(1, gate_count + 1))
    attempt_value_header_cells = f"""
      <th class="slalom-start-finish">старт</th>
      {gate_headers}
      <th class="slalom-start-finish">финиш</th>
"""
    attempt_1_cells = _slalom_attempt_value_cells(form_id, 1, run_by_attempt.get(1), gate_count)
    attempt_2_cells = _slalom_attempt_value_cells(form_id, 2, run_by_attempt.get(2), gate_count)
    return f"""
<tr data-slalom-form="{form_id}" data-slalom-team="{escape(team.name)}">
  <td rowspan="5" class="slalom-no{no_status_class}" data-slalom-no>
    <div class="slalom-no-label">№ команды</div>
    <div class="slalom-no-value">{team.start_number}</div>
  </td>
  <td colspan="4" rowspan="5" class="slalom-team-block">
    <div class="slalom-team-stack">
      <div class="slalom-name">{escape(team.name)}</div>
      <div class="slalom-subject">{escape(team.region)}</div>
      <div class="slalom-lineup crew-cell protocol-crew">
        <div>
          <span class="slalom-lineup-label">состав команды</span>
          <a class="slalom-lineup-link" href="{lineup_href}">Состав</a>
        </div>
      </div>
    </div>
  </td>
  <td rowspan="5" class="slalom-place">
    <div class="slalom-place-stack">
      <div class="slalom-place-row">
        <div class="slalom-place-label">Результат</div>
        <div class="slalom-place-metric" data-slalom-result>{escape(result_text)}</div>
      </div>
      <div class="slalom-place-row">
        <div class="slalom-place-label">Итог</div>
        <div class="slalom-place-metric" data-slalom-total>{escape(total_text)}</div>
      </div>
      <div class="slalom-place-row">
        <div class="slalom-place-label">Место</div>
        <div class="slalom-place-value" data-slalom-place>{place_text}</div>
      </div>
    </div>
  </td>
</tr>
<tr class="slalom-attempt-header-row{' slalom-attempt-best' if best_attempt_number == 1 else ''}" data-slalom-form="{form_id}" data-slalom-attempt="1">
  <th class="slalom-attempt-name">1я попытка</th>
  <th class="slalom-start-finish">старт</th>
  {gate_headers}
  <th class="slalom-start-finish">финиш</th>
</tr>
<tr class="slalom-attempt-value-row{' slalom-attempt-best' if best_attempt_number == 1 else ''}" data-slalom-form="{form_id}" data-slalom-attempt="1">
  {_slalom_attempt_value_cells(form_id, 1, run_by_attempt.get(1), gate_count, best_attempt_number == 1)}
</tr>
<tr class="slalom-attempt-header-row{' slalom-attempt-best' if best_attempt_number == 2 else ''}" data-slalom-form="{form_id}" data-slalom-attempt="2">
  <th class="slalom-attempt-name">2я попытка</th>
  <th class="slalom-start-finish">старт</th>
  {gate_headers}
  <th class="slalom-start-finish">финиш</th>
</tr>
<tr class="slalom-attempt-value-row{' slalom-attempt-best' if best_attempt_number == 2 else ''}" data-slalom-form="{form_id}" data-slalom-attempt="2">
  {_slalom_attempt_value_cells(form_id, 2, run_by_attempt.get(2), gate_count, best_attempt_number == 2)}
</tr>
<tr class="slalom-card-gap"><td colspan="100"></td></tr>
"""


def _slalom_attempt_value_cells(
    form_id: str,
    attempt_number: int,
    run: object | None,
    gate_count: int,
    is_best_attempt: bool = False,
) -> str:
    base_time = _format_hhmmss(getattr(run, "base_time_seconds", 0)) if run is not None else ""
    finish_time = ""
    if run is not None and hasattr(run, "finish_time_seconds"):
        finish_time = _format_hhmmss(getattr(run, "finish_time_seconds", 0))
    gate_cells = "".join(
        _slalom_gate_select_html(
            form_id=form_id,
            name=f"attempt_{attempt_number}_gate_{gate_index}",
            selected=getattr(run, "gate_penalties", [])[gate_index - 1] if run is not None and gate_index - 1 < len(getattr(run, "gate_penalties", [])) else 0,
        )
        for gate_index in range(1, gate_count + 1)
    )
    return f"""
<td class="slalom-attempt-spacer" data-slalom-best-cell>{'<span class="slalom-best-badge">лучшая</span>' if is_best_attempt else ''}</td>
<td class="slalom-start-finish"><input class="inline-time" form="{form_id}" data-time-mask="hhmmss" name="attempt_{attempt_number}_base_time_seconds" value="{escape(base_time)}" placeholder="00:00:00" /></td>
{gate_cells}
<td class="slalom-start-finish"><input class="inline-time" form="{form_id}" data-time-mask="hhmmss" name="attempt_{attempt_number}_finish_time_seconds" value="{escape(finish_time)}" placeholder="00:00:00" /></td>
"""


def _slalom_gate_select_html(form_id: str, name: str, selected: int) -> str:
    options = "".join(
        f'<button type="button" class="slalom-penalty-option" data-value="{value}">{value}</button>'
        for value in (0, 5, 50)
    )
    return f"""
<td class="slalom-gate">
  <div class="slalom-penalty-picker">
    <input type="hidden" form="{form_id}" name="{name}" value="{selected}" />
    <button type="button" class="slalom-penalty-trigger">{selected}</button>
    <div class="slalom-penalty-menu">{options}</div>
  </div>
</td>
"""


def _slalom_lineup_panel_html(
    db_name: str,
    category_key: str,
    team: Team,
    lineup: list[dict[str, object]],
) -> str:
    active_items = [item for item in lineup if bool(item["is_active"])]
    inactive_items = [item for item in lineup if not bool(item["is_active"])]
    active_html = "".join(
        _sprint_lineup_member_control(db_name, category_key, team.name, item, "убрать", False, "/slalom/lineup")
        for item in active_items
    ) or '<li class="subtle">Пусто</li>'
    inactive_html = "".join(
        _sprint_lineup_member_control(db_name, category_key, team.name, item, "вернуть", True, "/slalom/lineup")
        for item in inactive_items
    ) or '<li class="subtle">Пусто</li>'
    return f"""
<section id="slalom-lineup" class="panel-card parallel-lineup-panel slalom-lineup-panel">
  <div class="section-head">
    <div>
      <h2>Состав команды</h2>
      <p class="subtle">{escape(team.name)} · № {team.start_number}</p>
    </div>
    <a class="secondary-link" href="/slalom?db={quote(db_name)}&category={quote(category_key)}">Скрыть</a>
  </div>
  <div class="parallel-lineup-grid">
    <div>
      <strong>В старте</strong>
      <ul class="compact-list lineup-list">{active_html}</ul>
    </div>
    <div>
      <strong>Вне старта</strong>
      <ul class="compact-list lineup-list">{inactive_html}</ul>
    </div>
  </div>
</section>
"""


def _parallel_sprint_results_protocol_row(
    team: Team,
    result_data: tuple[ParallelSprintHeatResult, ParallelSprintHeatMeta | None, str] | None,
    place: int | None,
    lineup: list[dict[str, object]],
) -> str:
    lineup_text = "<br />".join(_active_lineup_labels(lineup)) or "Состав не определен"
    base_time = ""
    penalty = ""
    total = ""
    if result_data is not None:
        entry, meta, lane = result_data
        total = _format_mmss(entry.total_time_seconds)
        if meta is not None:
            if lane == "left":
                base_time = _format_mmss(meta.left_base_time_seconds)
                penalty = _format_mmss(meta.left_penalty_seconds)
            else:
                base_time = _format_mmss(meta.right_base_time_seconds)
                penalty = _format_mmss(meta.right_penalty_seconds)
    points = points_for_place("parallel_sprint", place) if place else 0
    place_text = str(place) if place else ""
    return f"""
<tr>
  <td class="col-number">{team.start_number}</td>
  <td>{escape(team.name)}</td>
  <td class="crew-cell protocol-crew">{lineup_text}</td>
  <td>{escape(team.region)}</td>
  <td class="col-time">{escape(base_time)}</td>
  <td class="col-time">{escape(penalty)}</td>
  <td class="col-time">{escape(total)}</td>
  <td class="col-place">{place_text}</td>
  <td class="col-place">{points}</td>
</tr>
"""


def _combined_results_protocol_row(
    team: Team,
    sprint_place: int | None,
    sprint_points: int,
    parallel_place: int | None,
    parallel_points: int,
    slalom_place: int | None,
    slalom_points: int,
    long_race_place: int | None,
    long_race_points: int,
    combined_place: int | None,
    combined_points: int,
) -> str:
    main_members = [member for member in team.crew_members if member.role != "reserve"]
    lineup_text = "<br />".join(_team_member_protocol_labels(main_members)) or "Состав не определен"
    return f"""
<tr>
  <td class="col-number">{team.start_number}</td>
  <td>{escape(team.name)}</td>
  <td class="crew-cell protocol-crew">{lineup_text}</td>
  <td>{escape(team.region)}</td>
  <td class="col-discipline discipline-cell">{_discipline_cell(sprint_place, sprint_points)}</td>
  <td class="col-discipline discipline-cell">{_discipline_cell(parallel_place, parallel_points)}</td>
  <td class="col-discipline discipline-cell">{_discipline_cell(slalom_place, slalom_points)}</td>
  <td class="col-discipline discipline-cell">{_discipline_cell(long_race_place, long_race_points)}</td>
  <td class="col-discipline discipline-cell">{_discipline_cell(combined_place, combined_points)}</td>
</tr>
"""


def _sprint_status_select(
    field_name: str,
    selected_value: str,
    disabled: bool = False,
    extra_class: str = "",
) -> str:
    canonical_value = _status_option_value(selected_value)
    options = [
        ("OK", "Финиш"),
        ("DNS", "Не старт"),
        ("DNF", "Не финиш"),
        ("DSQ", "Дисквалификация"),
    ]
    html = "".join(
        f"<option value=\"{value}\" {'selected' if value == canonical_value else ''}>{label}</option>"
        for value, label in options
    )
    class_attr = f' class="{escape(extra_class)}"' if extra_class else ""
    disabled_attr = ' disabled="disabled"' if disabled else ""
    return f"<select name=\"{escape(field_name)}\"{class_attr}{disabled_attr}>{html}</select>"


def _long_race_group_select(field_name: str, selected_value: int) -> str:
    options = "".join(
        f"<option value=\"{value}\" {'selected' if value == selected_value else ''}>{value}</option>"
        for value in range(1, 11)
    )
    options += f"<option value=\"99\" {'selected' if selected_value == 99 else ''}>н/у</option>"
    return f"<select class=\"long-race-party-select\" name=\"{escape(field_name)}\">{options}</select>"


def _format_mmss(total_seconds: int) -> str:
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def _parse_mmss(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        return int(minutes or 0) * 60 + int(seconds or 0)
    return int(text)


def _parse_hhmmss(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    parts = text.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(seconds or 0)
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes or 0) * 60 + int(seconds or 0)
    return int(text or 0)


def _parse_hhmm(value: str) -> int:
    text = value.strip()
    if not text or ":" not in text:
        return 0
    hours, minutes = text.split(":", 1)
    return int(hours or 0) * 60 + int(minutes or 0)


def _format_hhmm(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _format_hhmmss(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _parse_lineup_target(value: str) -> tuple[str, int, bool]:
    team_name, separator, tail = value.partition("|")
    if not separator:
        return ("", 0, False)
    member_text, separator, active_text = tail.partition("|")
    if not separator:
        return ("", 0, False)
    return (team_name, int(member_text or 0), active_text == "1")


def _normalize_sprint_status(status: str) -> str:
    return {
        "OK": "OK",
        "DNS": "Н/СТ",
        "DNF": "Н/ФИН",
        "DSQ": "ДИСКВ/П",
        "Н/СТ": "Н/СТ",
        "Н/ФИН": "Н/ФИН",
        "ДИСКВ/П": "ДИСКВ/П",
        "ДИСКВ/С": "ДИСКВ/С",
    }.get(status, status)


def _status_option_value(status: str) -> str:
    return {
        "OK": "OK",
        "DNS": "DNS",
        "DNF": "DNF",
        "DSQ": "DSQ",
        "Н/СТ": "DNS",
        "Н/ФИН": "DNF",
        "ДИСКВ/П": "DSQ",
        "ДИСКВ/С": "DSQ",
    }.get(status, "OK")


def _active_lineup_names(lineup: list[dict[str, object]]) -> list[str]:
    names: list[str] = []
    for item in lineup:
        if not bool(item["is_active"]):
            continue
        member = item["member"]
        if isinstance(member, TeamMember) and member.full_name:
            names.append(member.full_name)
    return names


def _active_lineup_labels(lineup: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for item in lineup:
        if not bool(item["is_active"]):
            continue
        member = item["member"]
        if not isinstance(member, TeamMember):
            continue
        parts = [member.full_name]
        if member.birth_date:
            parts.append(member.birth_date[:4])
        if member.rank:
            parts.append(member.rank)
        labels.append(escape(", ".join(part for part in parts if part)))
    return labels


def _compact_protocol_rank(rank: str) -> str:
    return {
        "1 разряд": "1р",
        "2 разряд": "2р",
        "3 разряд": "3р",
        "1 юношеский": "1юр",
        "2 юношеский": "2юр",
        "3 юношеский": "3юр",
    }.get(rank, rank)


def _active_slalom_protocol_labels(lineup: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for item in lineup:
        if not bool(item["is_active"]):
            continue
        member = item["member"]
        if not isinstance(member, TeamMember):
            continue
        parts = [member.full_name]
        if member.birth_date:
            parts.append(member.birth_date[:4])
        if member.rank:
            parts.append(_compact_protocol_rank(member.rank))
        labels.append(escape(", ".join(part for part in parts if part)))
    return labels


def _team_member_protocol_labels(members: list[TeamMember]) -> list[str]:
    labels: list[str] = []
    for member in members:
        parts = [member.full_name]
        if member.birth_date:
            parts.append(member.birth_date[:4])
        if member.rank:
            parts.append(member.rank)
        labels.append(escape(", ".join(part for part in parts if part)))
    return labels


def _discipline_cell(place: int | None, points: int) -> str:
    if place is None and points == 0:
        return ""
    place_text = str(place) if place is not None else "-"
    return f'{place_text}<br /><span class="discipline-points">{points}</span>'


def _long_race_points_for_entry(entry: SprintEntry | None, place: int | None) -> int:
    if entry is None or place is None:
        return 0
    if entry.start_order == 99 or _normalize_sprint_status(entry.status) == "Н/СТ":
        return 0
    return points_for_place("long_race", place)


def _sprint_note_from_status(status: str) -> str:
    return {
        "OK": "",
        "DNS": "Не старт",
        "DNF": "Не финиш",
        "DSQ": "Дисквалификация",
        "Н/СТ": "Не старт",
        "Н/ФИН": "Не финиш",
        "ДИСКВ/П": "Дисквалификация",
        "ДИСКВ/С": "Дисквалификация",
    }.get(status, "")


def _competition_dates_from_form(form_data: dict[str, str]) -> list[str]:
    items = [
        (key, value.strip())
        for key, value in form_data.items()
        if key.startswith("competition_date_") and value.strip()
    ]
    items.sort(key=lambda item: int(item[0].split("_")[-1]))
    return [value for _, value in items]


def _organizers_from_form(form_data: dict[str, str]) -> list[str]:
    items = [
        (key, value.strip())
        for key, value in form_data.items()
        if key.startswith("organizer_") and value.strip()
    ]
    items.sort(key=lambda item: int(item[0].split("_")[-1]))
    return [value for _, value in items]


def _first_competition_day(settings: CompetitionSettingsRecord) -> str:
    if settings.competition_dates:
        return settings.competition_dates[0]
    return settings.competition_date


def _team_category_block(
    db_name: str,
    category: Category,
    teams: list[Team],
    editing_team: Team | None,
    competition_date: str,
    active_category: str,
) -> str:
    age_min, age_max = _category_birth_year_range(category, competition_date)
    member_fields = "".join(
        _team_member_fields(
            index,
            "main",
            str(index),
            _member_or_empty(editing_team, index - 1, "main"),
            age_min,
            age_max,
        )
        for index in range(1, _crew_main_count(category.boat_class) + 1)
    ) + _team_member_fields(
        _crew_main_count(category.boat_class) + 1,
        "reserve",
        "Зап",
        _member_or_empty(editing_team, _crew_main_count(category.boat_class), "reserve"),
        age_min,
        age_max,
    )
    saved_cards = "".join(_saved_team_card(db_name, team) for team in teams) or "<p class=\"subtle\">Команд в этой категории пока нет.</p>"
    button_label = "Сохранить изменения" if editing_team else "Сохранить команду"
    open_attr = " open" if category.key == active_category else ""
    category_anchor = "category-" + category.key.replace(":", "-")
    return f"""
<details class="panel-card" id="{category_anchor}"{open_attr}>
  <summary class="section-head">
    <div>
      <h2>{escape(_category_label(category))}</h2>
      <p class="subtle">{len(teams)} команд</p>
    </div>
    <span class="secondary-link card-button">+ Добавить команду</span>
  </summary>
  <form method="post" action="/teams/add" class="stack-form">
    <input type="hidden" name="db" value="{escape(db_name)}" />
    <input type="hidden" name="boat_class" value="{escape(category.boat_class)}" />
    <input type="hidden" name="sex" value="{escape(category.sex)}" />
    <input type="hidden" name="age_group" value="{escape(category.age_group)}" />
    <input type="hidden" name="editing_category_key" value="{escape(editing_team.category_key if editing_team else '')}" />
    <input type="hidden" name="editing_start_number" value="{editing_team.start_number if editing_team else ''}" />
    <div class="team-form-grid">
      <label>Название команды <input name="name" value="{escape(editing_team.name if editing_team else '')}" /></label>
      <label>Номер <input name="start_number" value="{editing_team.start_number if editing_team else ''}" /></label>
      <label>Клуб <input name="club" value="{escape(editing_team.club if editing_team else '')}" /></label>
      <label>Субъект РФ <input name="region" value="{escape(editing_team.region if editing_team else '')}" /></label>
      <label>Представитель команды (ФИО) <input name="representative_full_name" value="{escape(editing_team.representative_full_name if editing_team else '')}" /></label>
    </div>
    <div class="team-card">
      <h3>Состав команды</h3>
      <div class="judge-grid">
        {member_fields}
      </div>
    </div>
    <button type="submit">{button_label}</button>
  </form>
  <div class="team-card-list">
    {saved_cards}
  </div>
</details>
"""


def _team_member_fields(
    index: int,
    role: str,
    label: str,
    member: TeamMember | None,
    age_min: int | None,
    age_max: int | None,
) -> str:
    selected_rank = member.rank if member and member.rank in SPORT_RANK_OPTIONS else ""
    birth_value = (member.birth_date[:4] if member and member.birth_date else "")
    age_attrs = ""
    if age_min is not None and age_max is not None:
        age_attrs = f' data-age-min="{age_min}" data-age-max="{age_max}"'
    reserve_class = " reserve-card" if role == "reserve" else ""
    return f"""
<section class="judge-card{reserve_class}">
  <div class="member-row">
    <div class="member-index">
      <label>{"Зап" if role == "reserve" else "№"}</label>
      <div class="member-index-value">{escape(label)}</div>
    </div>
    <label>ФИО <input name="member_{index}_full_name" value="{escape(member.full_name if member else '')}" /></label>
    <label>Год рождения <input name="member_{index}_birth_date" inputmode="numeric" maxlength="4" placeholder="2008" value="{escape(birth_value)}"{age_attrs} /><div class="year-warning"></div></label>
    <label>Разряд {_sport_rank_select(f"member_{index}_rank", selected_rank or "Б/Р")}</label>
    <input type="hidden" name="member_{index}_role" value="{escape(role)}" />
  </div>
</section>
"""


def _crew_main_count(boat_class: str) -> int:
    return 6 if boat_class.upper() == "R6" else 4


def _team_members_from_form(form_data: dict[str, str]) -> list[TeamMember]:
    indexes = sorted(
        {
            int(key.split("_")[1])
            for key in form_data
            if key.startswith("member_") and key.endswith("_full_name")
        }
    )
    members: list[TeamMember] = []
    for index in indexes:
        full_name = form_data.get(f"member_{index}_full_name", "").strip()
        birth_date = form_data.get(f"member_{index}_birth_date", "").strip()[:4]
        rank = form_data.get(f"member_{index}_rank", "Б/Р").strip() or "Б/Р"
        role = form_data.get(f"member_{index}_role", "main").strip() or "main"
        if any([full_name, birth_date, rank]):
            members.append(TeamMember(full_name=full_name, birth_date=birth_date, rank=rank, role=role))
    return members


def _saved_team_card(db_name: str, team: Team) -> str:
    members = team.crew_members
    member_rows = "".join(
        f"<li>{escape(member.full_name or 'Не заполнено')} - {escape(member.birth_date or 'дата не указана')} - {escape(member.rank or 'разряд не указан')}</li>"
        for member in members
    ) or "<li>Состав не заполнен</li>"
    return f"""
<details class="team-card">
  <summary class="team-card-head">
    <div>
      <h3>{escape(team.name)} #{team.start_number}</h3>
      <p class="subtle">{escape(team.club or 'Клуб не указан')} · {escape(team.region or 'Регион не указан')}</p>
    </div>
    <div class="team-actions">
      <a class="secondary-link inline-action" href="/teams?db={escape(db_name)}&edit_category={quote(team.category_key)}&edit_number={team.start_number}#category-{team.category_key.replace(':', '-')}">Редактировать</a>
      <a class="secondary-link inline-action" href="/teams/delete?db={escape(db_name)}&category={quote(team.category_key)}&start_number={team.start_number}">Удалить</a>
    </div>
  </summary>
  <div class="team-meta">
    <div><strong>Представитель</strong><br />{escape(team.representative_full_name or 'Не указан')}</div>
    <div><strong>Участников</strong><br />{len([member for member in members if member.full_name])}</div>
  </div>
  <ul class="compact-list roomy">{member_rows}</ul>
</details>
"""


def _editing_team_for_category(
    teams: list[Team],
    editing_category: str,
    editing_number: int,
    current_category: str,
) -> Team | None:
    if editing_category != current_category or editing_number <= 0:
        return None
    for team in teams:
        if team.start_number == editing_number:
            return team
    return None


def _member_or_empty(team: Team | None, index: int, role: str) -> TeamMember | None:
    if team is None:
        return None
    members = team.crew_members
    if index < len(members):
        return members[index]
    if role == "reserve":
        reserve_members = [member for member in members if member.role == "reserve"]
        return reserve_members[0] if reserve_members else None
    return None


def _sport_rank_select(field_name: str, selected_value: str) -> str:
    options = "".join(
        f"<option value=\"{escape(value)}\" {'selected' if value == selected_value else ''}>{escape(value)}</option>"
        for value in SPORT_RANK_OPTIONS
    )
    return f"<select name=\"{escape(field_name)}\">{options}</select>"


def _category_birth_year_range(category: Category, competition_date: str) -> tuple[int | None, int | None]:
    age_limits = {
        "U16": (12, 15),
        "U20": (14, 19),
        "U24": (14, 23),
    }
    if category.age_group not in age_limits:
        return (None, None)
    try:
        competition_year = int((competition_date or "").split("-")[0])
    except ValueError:
        competition_year = 2026
    min_age, max_age = age_limits[category.age_group]
    return (competition_year - max_age, competition_year - min_age)

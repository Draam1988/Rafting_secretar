# Judges Screen Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить полноценный экран `Судьи` с хранением обязательных ролей и остального судейского состава, а также статусом на рабочем столе.

**Architecture:** Хранение судей добавить в SQLite отдельными таблицами для обязательных ролей и обычных судей. Web-экран `Судьи` должен читать и сохранять эти данные через отдельный storage-модуль, а рабочий стол должен вычислять статус блока по заполненности ролей и списка.

**Tech Stack:** Python, SQLite, WSGI, pytest, текущий HTML/CSS в `raftsecretary/web/app.py`

---

### Task 1: Add failing storage tests

**Files:**
- Create: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/storage/test_judges_storage.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/schema.sql`

**Step 1: Write the failing test**

Покрыть:
- сохранение и загрузку обязательных ролей;
- сохранение и загрузку списка остальных судей.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/storage/test_judges_storage.py -q`

Expected: FAIL, потому что storage-модуля и таблиц пока нет.

**Step 3: Write minimal implementation**

Добавить:
- таблицы в `schema.sql`;
- storage-модуль с `save_judges(...)` и `load_judges(...)`.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/storage/test_judges_storage.py -q`

Expected: PASS

### Task 2: Add failing web tests

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_dashboard_links.py`
- Create: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_judges_flow.py`

**Step 1: Write the failing test**

Покрыть:
- GET `/judges` показывает обязательные роли и кнопку `Добавить судью`;
- POST `/judges/save` сохраняет данные и делает redirect обратно;
- dashboard меняет статус блока `Судьи`.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/web/test_judges_flow.py tests/web/test_dashboard_links.py -q`

Expected: FAIL, потому что POST-маршрута и реального рендера еще нет.

**Step 3: Write minimal implementation**

Добавить маршрут, рендер формы и подсчет статуса.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/web/test_judges_flow.py tests/web/test_dashboard_links.py -q`

Expected: PASS

### Task 3: Implement storage and schema

**Files:**
- Create: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/judges_storage.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/schema.sql`

**Step 1: Add schema**

Таблицы:
- `required_judges(role_key, last_name, first_name, patronymic, category)`
- `judges(id, display_order, last_name, first_name, patronymic, category)`

**Step 2: Add storage API**

Нужные функции:
- `load_judges(db_path)`
- `save_judges(db_path, required_roles, judges)`

**Step 3: Keep implementation minimal**

Без истории изменений, без удаления по id, без сложной нормализации.

**Step 4: Run storage tests**

Run: `python3 -m pytest tests/storage/test_judges_storage.py -q`

Expected: PASS

### Task 4: Implement judges screen

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Add GET and POST flow**

Маршруты:
- `GET /judges`
- `POST /judges/save`

**Step 2: Render page**

Сделать:
- шапку страницы;
- обязательные роли отдельными карточками;
- секцию `Остальные судьи`;
- кнопку `Добавить судью`;
- dropdown категории.

**Step 3: Redirect after save**

После сохранения:
- `303 See Other`
- назад на `/judges?db=...`

**Step 4: Run web tests**

Run: `python3 -m pytest tests/web/test_judges_flow.py tests/web/test_dashboard_links.py -q`

Expected: PASS

### Task 5: Update dashboard status

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_ui_shell.py`

**Step 1: Add status logic**

Логика:
- red: не заполнены обязательные роли
- yellow: обязательные роли заполнены, но список судей пуст
- green: обязательные роли заполнены и есть обычные судьи

**Step 2: Render correct short detail**

Тексты:
- `Не заполнено`
- `Только обязательные роли`
- `Состав заполнен`

**Step 3: Run targeted tests**

Run: `python3 -m pytest tests/web/test_ui_shell.py tests/web/test_judges_flow.py -q`

Expected: PASS

### Task 6: Final verification and docs

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/Context.md`

**Step 1: Run full tests**

Run: `python3 -m pytest tests -q`

Expected: PASS

**Step 2: Update context**

Добавить:
- что реализован экран `Судьи`;
- что добавлен storage и dashboard status;
- текущее число тестов.

**Step 3: Commit**

```bash
git add /Users/pavel/Desktop/Codex_Rafting/Context.md /Users/pavel/Desktop/Codex_Rafting/docs/plans/2026-03-15-judges-screen-design.md /Users/pavel/Desktop/Codex_Rafting/docs/plans/2026-03-15-judges-screen-implementation.md /Users/pavel/Desktop/Codex_Rafting/RaftSecretary
git commit -m "feat: add judges management screen"
```

# Teams Screen Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Переделать блок `Команды` под независимые категории соревнования, полноценные карточки команд и детальный состав экипажа.

**Architecture:** Хранение команд нужно расширить: оставить привязку к категории, но заменить примитивный список `athletes` на структурированных участников с датой рождения, разрядом и ролью запасного. UI должен строиться по категориям из `competition_settings`, а каждая категория должна иметь собственную форму добавления и список карточек команд.

**Tech Stack:** Python, SQLite, pytest, текущий WSGI app, HTML/CSS в `raftsecretary/web/app.py`

---

### Task 1: Expand domain and storage tests

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/storage/test_team_storage.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/domain/models.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/schema.sql`

**Step 1: Write failing tests**

Покрыть:
- команду с `club`, `representative_full_name`;
- участников с `full_name`, `birth_date`, `rank`, `role`;
- корректную загрузку/сохранение `R4` и `R6`.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/storage/test_team_storage.py -q`

Expected: FAIL

### Task 2: Implement richer team storage

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/domain/models.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/schema.sql`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/team_storage.py`

**Step 1: Add richer models**

Добавить структуру участника команды и расширить `Team`.

**Step 2: Update schema**

Добавить в `teams`:
- `club`
- `representative_full_name`

Заменить текущую модель `athletes` или расширить ее до:
- `member_order`
- `role`
- `full_name`
- `birth_date`
- `rank`

**Step 3: Add legacy compatibility**

Старые `.db` не должны ломаться.

### Task 3: Redesign teams screen tests

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_settings_and_teams.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_edit_flows.py`
- Create: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_team_delete_flow.py`

**Step 1: Write failing tests**

Покрыть:
- вывод только выбранных категорий;
- раскрываемые блоки категорий;
- форма команды для `R4` и `R6`;
- сохранение команды в нужную категорию;
- карточку сохраненной команды;
- удаление с подтверждением.

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/web/test_settings_and_teams.py tests/web/test_edit_flows.py tests/web/test_team_delete_flow.py -q`

Expected: FAIL

### Task 4: Implement teams UI

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Render categories as full-width collapsible blocks**

В заголовке:
- название категории
- число команд
- `+ Добавить команду`

**Step 2: Render inline team form**

Поля:
- название
- номер
- клуб
- региональная принадлежность
- представитель команды

Состав:
- `4+1` или `6+1` по классу судна

**Step 3: Render saved team cards**

Компактная карточка + раскрытие состава.

### Task 5: Add edit/delete flows

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Add edit behavior**

Для MVP допустимо:
- открывать форму редактирования прямо внутри категории;
- пересохранять всю команду.

**Step 2: Add delete confirmation**

По аналогии с удалением файла соревнования:
- отдельный экран подтверждения
- POST delete

### Task 6: Verify and document

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/Context.md`

**Step 1: Run full tests**

Run: `python3 -m pytest tests -q`

Expected: PASS

**Step 2: Update context**

Добавить описание нового блока `Команды`.

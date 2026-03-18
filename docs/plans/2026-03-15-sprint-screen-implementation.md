# Sprint Screen Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Переделать блок `Спринт` в рабочий экран секретаря со стартовым порядком, жеребьевкой и построчным вводом результатов.

**Architecture:** Использовать существующее sprint storage, но расширить web-flow от одиночной формы к табличному вводу по категории. Стартовый порядок хранить в sprint entries через `start_order`, а экран строить из команд выбранной категории, объединяя данные команды и уже сохраненные sprint results.

**Tech Stack:** Python, pytest, текущий WSGI app, SQLite storage, HTML/CSS в `raftsecretary/web/app.py`

---

### Task 1: Add failing web tests for sprint table

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_sprint_flow.py`
- Create: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_sprint_draw_flow.py`

**Step 1: Write failing tests**

Покрыть:
- экран показывает все команды категории сразу;
- есть колонка стартового номера;
- есть штраф за неспортивное поведение;
- есть dropdown статуса.

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/web/test_sprint_flow.py tests/web/test_sprint_draw_flow.py -q`

Expected: FAIL

### Task 2: Add draw and reorder behavior

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Add draw action**

Добавить POST route:
- `POST /sprint/draw`

Поведение:
- случайно проставить `№ старта` для всех команд категории.

**Step 2: Add reroll action**

Можно использовать тот же route с флагом или отдельный `POST /sprint/redraw`.

### Task 3: Render sprint as inline table

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Replace single-entry form**

Сделать таблицу всех команд категории.

Колонки:
- `№ старта`
- `Команда`
- `№ команды`
- `Состав`
- `Субъект РФ`
- `Время`
- `Штраф за неспортивное поведение`
- `Результат`
- `Статус`

**Step 2: Make crew column compact**

Мелкий шрифт, перенос строк допустим.

### Task 4: Save row results

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Keep current storage API**

Использовать существующее `save_sprint_entries(...)`, но строить массив из таблицы.

**Step 2: Result calculation**

Считать автоматически:
- `result = time + behavior_penalty`

### Task 5: Verification and docs

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/Context.md`

**Step 1: Run full tests**

Run: `python3 -m pytest tests -q`

Expected: PASS

**Step 2: Update context**

Добавить:
- что `Спринт` теперь рабочий табличный экран;
- что стартовый порядок можно жеребить и править вручную.

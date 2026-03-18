# Home Competition Delete Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить удаление файлов соревнований с главного экрана, с отображением имени без `.db` и обязательным подтверждением.

**Architecture:** Стартовый экран продолжает читать локальные `.db` из папки `data`, но теперь для каждого файла строит две операции: открыть и удалить. Удаление выполняется POST-запросом с подтверждением на отдельном экране, чтобы исключить случайное удаление по ссылке.

**Tech Stack:** Python, pathlib, текущий WSGI-сервер, HTML/CSS в `raftsecretary/web/app.py`, pytest

---

### Task 1: Add failing tests

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_ui_shell.py`
- Create: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_delete_competition_flow.py`

**Step 1: Write the failing test**

Покрыть:
- список соревнований без `.db`;
- наличие крестика удаления;
- GET-экран подтверждения;
- POST-удаление файла и возврат на главную.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/web/test_ui_shell.py tests/web/test_delete_competition_flow.py -q`

Expected: FAIL

### Task 2: Implement delete flow

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/db.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Add delete helper**

Добавить безопасное удаление `.db` по имени файла.

**Step 2: Add routes**

Маршруты:
- `GET /competitions/delete?db=...`
- `POST /competitions/delete`

**Step 3: Update home UI**

Список:
- имя без `.db`;
- ссылка на открытие;
- кнопка `×` для удаления.

**Step 4: Add confirmation screen**

Показать:
- имя соревнования без `.db`;
- `Удалить`
- `Отмена`

### Task 3: Verify and document

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/Context.md`

**Step 1: Run full tests**

Run: `python3 -m pytest tests -q`

Expected: PASS

**Step 2: Update context**

Добавить запись про удаление соревнований со стартового экрана.

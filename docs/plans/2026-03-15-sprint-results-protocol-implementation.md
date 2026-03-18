# Sprint Results Protocol Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Собрать раздел `Протоколы` и добавить в него `Итоговый протокол спринта` как HTML-документ на одной странице по всем категориям.

**Architecture:** Использовать существующие данные соревнования, команд, спринта и стартового состава спринта. Раздел `Протоколы` станет реестром документов, а маршрут итогового протокола будет строить HTML из уже сохраненных данных без отдельного слоя экспорта.

**Tech Stack:** Python, WSGI, встроенный HTML-рендер в `app.py`, SQLite storage, pytest.

---

### Task 1: Добавить тест на реестр документов

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_ui_shell.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Write the failing test**

Проверить, что `/export?db=...` показывает список документов и ссылку на итоговый протокол спринта.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/web/test_ui_shell.py -q`

**Step 3: Write minimal implementation**

Заменить заглушку `Протоколы` на список документов.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/web/test_ui_shell.py -q`

### Task 2: Добавить тест на итоговый протокол спринта

**Files:**
- Create/Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_sprint_results_protocol.py`
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Write the failing test**

Проверить, что маршрут итогового протокола:
- показывает шапку соревнования;
- выводит категорию;
- выводит стартовый состав спринта;
- выводит место и очки.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/web/test_sprint_results_protocol.py -q`

**Step 3: Write minimal implementation**

Добавить новый GET-маршрут и HTML-страницу протокола.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/web/test_sprint_results_protocol.py -q`

### Task 3: Подключить стартовый состав спринта к протоколу

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`
- Reuse: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/sprint_storage.py`

**Step 1: Write the failing test**

Проверить, что в протокол попадает не весь состав команды, а только участники `В старте`.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/web/test_sprint_results_protocol.py -q`

**Step 3: Write minimal implementation**

Использовать уже сохраненные флаги стартового состава и собирать строку состава только из активных участников.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/web/test_sprint_results_protocol.py -q`

### Task 4: Полная проверка

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/Context.md`

**Step 1: Run full tests**

Run: `python3 -m pytest tests -q`

**Step 2: Update context**

Зафиксировать, что `Протоколы` и первый итоговый документ уже есть.

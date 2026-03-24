# Import Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Разрешать импорт баз с совместимой схемой, но явно предупреждать, если файл создан другой версией приложения.

**Architecture:** `schema_version` остается техническим критерием блокировки, а `app_version` используется как информирование пользователя после успешного импорта. Логика чтения метаданных живет в storage, а web-слой только показывает баннер.

**Tech Stack:** Python, SQLite, текущий WSGI app, pytest

---

### Task 1: Add failing import warning tests

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_home.py`

**Step 1: Write the failing tests**

Покрыть:
- успешный импорт базы с той же схемой, но другой `app_version`;
- redirect на `/?import_notice=version_mismatch`;
- баннер на главной странице для `import_notice=version_mismatch`.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_home.py -q`

Expected: FAIL

### Task 2: Return richer import compatibility result

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/storage/db.py`

**Step 1: Add metadata inspection helper**

Вернуть не только `ok/error`, но и признак:
- `compatible`
- `incompatible`
- `version_mismatch`

**Step 2: Keep old schema handling**

База без `app_version` не должна блокироваться.

### Task 3: Show import notice in UI

**Files:**
- Modify: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary/raftsecretary/web/app.py`

**Step 1: Handle notice on import**

Если схема совместима, но `app_version` отличается:
- импортировать файл;
- redirect на `/?import_notice=version_mismatch`.

**Step 2: Render notice banner**

На главной добавить баннер с простым текстом:
- файл создан другой версией приложения;
- структура базы совместима, но стоит проверить данные после открытия.

### Task 4: Verify

**Files:**
- None

**Step 1: Run focused tests**

Run: `python3 -m pytest /Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests/web/test_home.py -q`

Expected: PASS

**Step 2: Run broader regression tests**

Run: `python3 -m pytest /Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests -q`

Expected: PASS

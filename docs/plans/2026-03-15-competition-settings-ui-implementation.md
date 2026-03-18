# Competition Settings UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the competition settings screen compact with collapsible discipline/category sections and render only enabled discipline blocks on the dashboard.

**Architecture:** Keep the existing data model and storage. Change only the web layer behavior and presentation so the same stored settings drive both the settings screen summaries and dashboard block visibility.

**Tech Stack:** Python, local HTML rendering, existing storage layer, pytest

---

### Task 1: Update settings screen tests

**Files:**
- Modify: `tests/web/test_settings_and_teams.py`
- Modify: `tests/web/test_edit_flows.py`

**Steps:**
- Assert that discipline/category blocks are summary-driven.
- Assert enabled disciplines continue saving correctly.

### Task 2: Update dashboard tests

**Files:**
- Modify: `tests/web/test_ui_shell.py`

**Steps:**
- Assert disabled disciplines are not rendered.
- Assert enabled disciplines are rendered.

### Task 3: Implement collapsible settings sections

**Files:**
- Modify: `raftsecretary/web/app.py`

**Steps:**
- Replace always-open discipline/category blocks with collapsible sections.
- Show summary counts in headings.

### Task 4: Render dashboard dynamically

**Files:**
- Modify: `raftsecretary/web/app.py`

**Steps:**
- Keep core blocks always visible.
- Render discipline blocks only when enabled.

### Task 5: Verify

**Files:**
- None

**Steps:**
- Run focused tests.
- Run full test suite.


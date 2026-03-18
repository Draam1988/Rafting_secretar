# RaftSecretary MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first working offline version of RaftSecretary for a single rafting competition secretary, with correct scoring, bracket generation, result entry, and printable protocols.

**Architecture:** The application should be built as a local Python web app with SQLite storage. The key design rule is strict separation between domain logic and interface: all scoring, ranking, status handling, and bracket generation must live in a separate rules layer that can be tested without the UI.

**Tech Stack:** Python, SQLite, simple server-rendered HTML, lightweight JavaScript, local CSS assets, pytest

---

## Plan Principles

- Start with domain logic, not screens.
- Every calculation rule must be covered by tests before UI wiring.
- Keep the first version local-only and offline-only.
- Avoid premature packaging complexity until the core workflow is working.
- Prefer printable HTML first; convert to PDF later only if stable.

## Proposed Project Structure

Before implementation, use this file layout:

```text
RaftSecretary/
  app/
    templates/
    static/
  raftsecretary/
    domain/
    services/
    storage/
    web/
  tests/
    domain/
    services/
    storage/
    web/
  data/
  exports/
  docs/plans/
  server.py
  requirements.txt
  README.md
```

## Milestones

### Milestone 1: Skeleton and Local Runtime

**Outcome:** A local app starts on one machine, opens in browser, and can create or open a competition file.

**Work blocks:**
- create base project folders;
- create Python entrypoint and local server bootstrap;
- add SQLite connection layer;
- add competition file discovery in `data/`;
- add main screen with "new competition" and "open competition".

**Definition of done:**
- app starts locally with one command;
- browser opens working home screen;
- user can create a new empty competition database;
- user can reopen existing database from `data/`.

### Milestone 2: Core Domain Models

**Outcome:** The app has a tested domain model for competitions, categories, teams, disciplines, statuses, and points.

**Work blocks:**
- define competition entity;
- define category entity;
- define team entity;
- define discipline enum and status enum;
- define points table and tie-break helpers;
- define category rule that mixed crews are stored as men's category.

**Definition of done:**
- domain layer works without web layer;
- tests confirm category separation and points mapping;
- status behavior is encoded centrally, not duplicated across screens.

### Milestone 3: Teams and Competition Setup

**Outcome:** The secretary can configure a competition and enter teams.

**Work blocks:**
- build competition settings form;
- build categories selection flow;
- build team list table with filters;
- add create/edit/delete team actions;
- store athlete names and one competition-wide start number.

**Definition of done:**
- user can configure one competition with selected categories and disciplines;
- user can manage teams in each category;
- data persists after restart.

### Milestone 4: Sprint Engine

**Outcome:** Sprint can be fully entered and ranked correctly.

**Work blocks:**
- implement sprint result model;
- implement total-time calculation;
- implement status handling for sprint;
- implement ranking and tie-break by earlier start;
- build sprint result entry screen.

**Definition of done:**
- secretary can enter sprint results for one category;
- live table updates correctly;
- ranking and points match official rules.

### Milestone 5: Parallel Sprint Engine

**Outcome:** Parallel sprint bracket is generated and advanced automatically from sprint results.

**Work blocks:**
- implement stage qualification logic from sprint ranking;
- implement first-stage pairing;
- implement main bracket generation based on official bracket layouts;
- implement heat winner logic with statuses and penalties;
- implement final placement logic for eliminated teams;
- build bracket/result screen.

**Definition of done:**
- bracket is generated from sprint results without manual calculation;
- winners advance automatically;
- final placements are computed correctly.

### Milestone 6: Slalom Engine

**Outcome:** Slalom with two attempts and gate penalties works end-to-end.

**Work blocks:**
- implement two-attempt result model;
- implement per-gate penalties `0/5/50`;
- implement best-attempt selection;
- implement slalom tie-break chain;
- build slalom result entry screen.

**Definition of done:**
- secretary can enter both attempts;
- best attempt is chosen automatically;
- standings and points update correctly.

### Milestone 7: Long Race and Combined Ranking

**Outcome:** Long race results and overall combined standings work.

**Work blocks:**
- implement long-race result model;
- implement status and penalty logic;
- implement current combined ranking across enabled disciplines;
- implement tie-break by slalom result;
- build combined ranking screen.

**Definition of done:**
- long race can be entered;
- combined standings update automatically;
- disabled disciplines do not break ranking.

### Milestone 8: Export and Backup

**Outcome:** The secretary can print usable protocols and make backups.

**Work blocks:**
- create printable start protocol;
- create printable discipline results protocol;
- create printable combined protocol;
- add export/import of entire competition as JSON;
- store export files in `exports/`.

**Definition of done:**
- protocols are readable and print-friendly;
- JSON export restores the competition correctly;
- no internet dependency exists in export flow.

### Milestone 9: Safety, Recovery, and Packaging

**Outcome:** The app is reliable enough for real field use.

**Work blocks:**
- add dangerous-action confirmations;
- add automatic backup on key saves;
- add basic change log or last-action recovery;
- create start scripts for local launch;
- write operator README.

**Definition of done:**
- accidental deletion risk is reduced;
- user can recover from common mistakes;
- non-technical user can launch the app from local files.

## Execution Order

Implementation should follow this order:

1. Milestone 1
2. Milestone 2
3. Milestone 3
4. Milestone 4
5. Milestone 5
6. Milestone 6
7. Milestone 7
8. Milestone 8
9. Milestone 9

This order is important because the UI depends on tested domain rules, and exports depend on stable stored data.

## Detailed Task Map

### Task 1: Create repository skeleton

**Files:**
- Create: `RaftSecretary/raftsecretary/__init__.py`
- Create: `RaftSecretary/raftsecretary/domain/__init__.py`
- Create: `RaftSecretary/raftsecretary/services/__init__.py`
- Create: `RaftSecretary/raftsecretary/storage/__init__.py`
- Create: `RaftSecretary/raftsecretary/web/__init__.py`
- Create: `RaftSecretary/app/templates/.gitkeep`
- Create: `RaftSecretary/app/static/.gitkeep`
- Create: `RaftSecretary/tests/domain/.gitkeep`
- Create: `RaftSecretary/tests/services/.gitkeep`
- Create: `RaftSecretary/tests/storage/.gitkeep`
- Create: `RaftSecretary/tests/web/.gitkeep`
- Create: `RaftSecretary/data/.gitkeep`
- Create: `RaftSecretary/exports/.gitkeep`
- Create: `RaftSecretary/server.py`
- Create: `RaftSecretary/requirements.txt`
- Create: `RaftSecretary/README.md`

**Check:**
- project tree exists and is clean;
- local Python entrypoint can be added next without restructuring.

### Task 2: Define competition schema in domain layer

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/models.py`
- Create: `RaftSecretary/tests/domain/test_models.py`

**Implement:**
- competition model;
- category model;
- team model;
- athlete model;
- discipline identifiers;
- status identifiers.

**Check:**
- tests confirm categories are separate by class, sex, and age;
- tests confirm mixed crews map to men's category for this project.

### Task 3: Encode official points table

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/points.py`
- Create: `RaftSecretary/tests/domain/test_points.py`

**Implement:**
- points lookup by discipline and place;
- zero points from place 21 and below;
- helper for combined ranking.

**Check:**
- tests cover places 1, 2, 10, 20, 21.

### Task 4: Encode result statuses and placement behavior

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/status_rules.py`
- Create: `RaftSecretary/tests/domain/test_status_rules.py`

**Implement:**
- handling for `Н/ФИН`;
- handling for `Н/СТ`;
- handling for `ДИСКВ/П`;
- handling for `ДИСКВ/С`;
- sort order for special statuses when required by rules.

**Check:**
- tests confirm ranking consequences match rules.

### Task 5: Add SQLite storage bootstrap

**Files:**
- Create: `RaftSecretary/raftsecretary/storage/db.py`
- Create: `RaftSecretary/raftsecretary/storage/schema.sql`
- Create: `RaftSecretary/tests/storage/test_db_bootstrap.py`

**Implement:**
- create database file;
- initialize schema;
- open existing database;
- list databases in `data/`.

**Check:**
- test creates temp DB and reopens it successfully.

### Task 6: Add home screen and competition file flow

**Files:**
- Create: `RaftSecretary/raftsecretary/web/app.py`
- Create: `RaftSecretary/app/templates/home.html`
- Create: `RaftSecretary/tests/web/test_home.py`
- Modify: `RaftSecretary/server.py`

**Implement:**
- home page;
- "new competition";
- "open competition";
- basic navigation shell.

**Check:**
- browser route returns working HTML;
- tests confirm home page loads.

### Task 7: Add competition settings flow

**Files:**
- Create: `RaftSecretary/raftsecretary/services/competition_service.py`
- Create: `RaftSecretary/app/templates/competition_settings.html`
- Create: `RaftSecretary/tests/services/test_competition_service.py`

**Implement:**
- save title, date, description;
- enable categories;
- enable disciplines;
- set slalom gate count.

**Check:**
- data persists in DB;
- reloading screen shows saved settings.

### Task 8: Add team management

**Files:**
- Create: `RaftSecretary/raftsecretary/services/team_service.py`
- Create: `RaftSecretary/app/templates/teams.html`
- Create: `RaftSecretary/tests/services/test_team_service.py`
- Create: `RaftSecretary/tests/web/test_teams.py`

**Implement:**
- create/edit/delete team;
- filter by category;
- store athlete names;
- store single competition-wide start number.

**Check:**
- CRUD works;
- invalid category/team combinations are rejected.

### Task 9: Implement sprint calculation engine

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/sprint.py`
- Create: `RaftSecretary/tests/domain/test_sprint.py`

**Implement:**
- total time = base time + penalties;
- status override behavior;
- rank by result;
- tie-break by earlier start.

**Check:**
- tests cover normal, tied, and status-based results.

### Task 10: Add sprint entry screen

**Files:**
- Create: `RaftSecretary/raftsecretary/services/sprint_service.py`
- Create: `RaftSecretary/app/templates/sprint.html`
- Create: `RaftSecretary/tests/services/test_sprint_service.py`
- Create: `RaftSecretary/tests/web/test_sprint_page.py`

**Implement:**
- ordered team list;
- result form;
- live recalculated standings after save.

**Check:**
- sprint can be fully entered for one category from UI.

### Task 11: Implement parallel sprint qualification and pairing

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/parallel_sprint.py`
- Create: `RaftSecretary/tests/domain/test_parallel_sprint.py`

**Implement:**
- detect bracket size;
- determine first-stage participants;
- generate stage-one pairs;
- generate main bracket seeding.

**Check:**
- tests cover 3, 5, 6, 7, 8, 9, 12, 16 teams.

### Task 12: Add parallel sprint heat resolution

**Files:**
- Modify: `RaftSecretary/raftsecretary/domain/parallel_sprint.py`
- Create: `RaftSecretary/tests/domain/test_parallel_sprint_results.py`

**Implement:**
- winner calculation;
- handling of missed buoy, penalties, statuses;
- ranking of eliminated teams by last heat time.

**Check:**
- tests cover semifinal/final placements and non-final ranking.

### Task 13: Add parallel sprint UI

**Files:**
- Create: `RaftSecretary/raftsecretary/services/parallel_sprint_service.py`
- Create: `RaftSecretary/app/templates/parallel_sprint.html`
- Create: `RaftSecretary/tests/services/test_parallel_sprint_service.py`
- Create: `RaftSecretary/tests/web/test_parallel_sprint_page.py`

**Implement:**
- stage tabs;
- heat entry;
- automatic advancement in bracket.

**Check:**
- full category bracket can be run in UI.

### Task 14: Implement slalom calculation engine

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/slalom.py`
- Create: `RaftSecretary/tests/domain/test_slalom.py`

**Implement:**
- two attempts;
- per-gate penalties;
- attempt totals;
- best-attempt choice;
- tie-break chain.

**Check:**
- tests cover all tie-break levels.

### Task 15: Add slalom UI

**Files:**
- Create: `RaftSecretary/raftsecretary/services/slalom_service.py`
- Create: `RaftSecretary/app/templates/slalom.html`
- Create: `RaftSecretary/tests/services/test_slalom_service.py`
- Create: `RaftSecretary/tests/web/test_slalom_page.py`

**Implement:**
- per-team two-attempt entry;
- per-gate penalty inputs;
- highlight counted attempt.

**Check:**
- standings update correctly after each save.

### Task 16: Implement long race and combined ranking

**Files:**
- Create: `RaftSecretary/raftsecretary/domain/long_race.py`
- Create: `RaftSecretary/raftsecretary/domain/combined.py`
- Create: `RaftSecretary/tests/domain/test_long_race.py`
- Create: `RaftSecretary/tests/domain/test_combined.py`

**Implement:**
- long-race result logic;
- current combined points total;
- tie-break by slalom place.

**Check:**
- combined ranking works with missing disciplines.

### Task 17: Add long race and combined UI

**Files:**
- Create: `RaftSecretary/raftsecretary/services/long_race_service.py`
- Create: `RaftSecretary/raftsecretary/services/combined_service.py`
- Create: `RaftSecretary/app/templates/long_race.html`
- Create: `RaftSecretary/app/templates/combined.html`
- Create: `RaftSecretary/tests/web/test_long_race_page.py`
- Create: `RaftSecretary/tests/web/test_combined_page.py`

**Implement:**
- long-race entry screen;
- combined ranking table;
- category filters.

**Check:**
- secretary can complete entire competition flow from UI.

### Task 18: Add printable exports

**Files:**
- Create: `RaftSecretary/raftsecretary/services/export_service.py`
- Create: `RaftSecretary/app/templates/export_start_protocol.html`
- Create: `RaftSecretary/app/templates/export_discipline_protocol.html`
- Create: `RaftSecretary/app/templates/export_combined_protocol.html`
- Create: `RaftSecretary/tests/services/test_export_service.py`

**Implement:**
- printable HTML layouts;
- export start protocol;
- export discipline results;
- export combined results.

**Check:**
- exports render cleanly in browser print preview.

### Task 19: Add JSON backup and restore

**Files:**
- Create: `RaftSecretary/raftsecretary/services/backup_service.py`
- Create: `RaftSecretary/tests/services/test_backup_service.py`

**Implement:**
- export all competition data to JSON;
- import JSON into new DB;
- validate imported structure.

**Check:**
- backup round-trip preserves competition state.

### Task 20: Add safety and launch scripts

**Files:**
- Create: `RaftSecretary/start.command`
- Create: `RaftSecretary/start.bat`
- Modify: `RaftSecretary/README.md`
- Create: `RaftSecretary/tests/web/test_destructive_actions.py`

**Implement:**
- safe-delete confirmations;
- backup reminder or automatic backup;
- launch scripts;
- user instructions in README.

**Check:**
- non-technical user can launch and use app locally.

## Testing Strategy

Testing priority:

1. Domain logic tests
2. Storage tests
3. Service tests
4. Web route tests
5. Manual browser testing

Critical test areas:
- points table correctness;
- special statuses;
- sprint ties;
- parallel sprint bracket generation;
- slalom tie-break chain;
- combined ranking with skipped disciplines;
- backup restore integrity.

## Risks to Control Early

- Parallel sprint logic is the highest rule-risk area. Test it heavily before UI work.
- Export to direct PDF may be unstable on old systems. Keep printable HTML as fallback.
- If packaging becomes hard, delay packaging polish until after domain correctness is proven.
- Avoid embedding rules inside templates or route handlers.

## Recommended Build Sequence for Real Work

If implementation starts in a new session, use this practical order:

1. Create project skeleton
2. Build and test domain logic
3. Add SQLite persistence
4. Add settings and team management UI
5. Add sprint flow
6. Add parallel sprint flow
7. Add slalom flow
8. Add long race and combined standings
9. Add exports and backups
10. Add launch scripts and hardening

## Handoff Note

This plan is optimized for safe implementation of the MVP, not maximum speed at any cost. The core requirement is rule correctness under field conditions.


# Context

## Project

- Name: `RaftSecretary`
- Root: `/Users/pavel/Desktop/Codex_Rafting/RaftSecretary`
- Workspace: `/Users/pavel/Desktop/Codex_Rafting`
- Main rules source: `/Users/pavel/Desktop/Codex_Rafting/Pravila-rafting-Novye.pdf`
- H2H seeding source: `/Users/pavel/Downloads/Олимпийская система.docx`

## Product Position

- Local offline secretary tool for one rafting competition.
- Russian UI only.
- Priority order:
  - correctness of sports logic
  - offline reliability
  - secretary workflow convenience
  - visual polish

## Fixed Product Decisions

- Mixed crews are treated as men's category.
- Main screen:
  - `Открыть соревнование`
  - `Создать соревнование`
  - `Открыть последнее соревнование`
- Dashboard = secretary workspace with status-colored blocks.
- Status colors:
  - green = ready
  - yellow = partially filled
  - red = critical missing data
- `Экспорт` renamed to `Протоколы`.

## Important UI Invariants

- Do not switch back to English UI.
- Keep interfaces minimal and operational, not decorative.
- In `H2H`, do not break:
  - start card style
  - heat card style
  - rule: next stage appears only after current stage is fully completed
- In `Slalom`, keep the long Excel-like sheet layout, not card UI.

## Core Implemented Areas

- Competition settings
- Judges
- Teams and crews
- Sprint
- H2H / parallel sprint
- Slalom
- Long race
- Combined ranking
- Protocols:
  - Sprint results
  - Slalom results
  - H2H results
  - Long race results
  - Combined results

## Settings / Competition Data

- Competition settings include:
  - name
  - organizer
  - venue
  - competition dates list
  - enabled disciplines
  - categories
  - slalom gate count
- Competition dates are structured fields, not one free-text string.

## Teams

- Teams are grouped by selected categories.
- Team fields:
  - team name
  - number
  - club
  - subject of RF
  - team representative
- Crew model:
  - `R4 = 4+1`
  - `R6 = 6+1`
- Birth year validation is by competition year only.

## Sprint

- Sprint is an operator table, not a one-team form.
- It supports:
  - full category table
  - start order
  - draw / redraw
  - inline result entry
  - separate sprint lineup (`В старте / Вне старта`)
- Sprint protocol is already built.

## H2H / Parallel Sprint

- H2H seeding logic was rebuilt to follow `/Users/pavel/Downloads/Олимпийская система.docx`.
- Bracket rebuilds correctly when team count changes.
- H2H UI is a board of stage columns, not a classic table.
- Current implemented behavior:
  - start column
  - stage columns
  - result editing inside the same stage column
  - heat winners/losers coloring
  - Final A / Final B
  - final ranked block after finals
- Clearing:
  - full protocol clear exists
  - per-stage clear exists and clears that stage plus all later stages
- Result logic:
  - 1st/2nd from Final A
  - 3rd/4th from Final B
  - lower places by elimination stage, then by heat time inside that stage
- H2H results protocol already exists.

## Long Race

- Long race is built from current combined standing.
- Tiebreak inside start ordering:
  - equal combined points -> better slalom place
- Long race uses the same operator-table style as Sprint.
- Long race results protocol already exists.

## Slalom

- Slalom is a long sheet-like table based on the user reference, not a compact form.
- Gate count is dynamic from competition settings.
- Gate cells use minimal picker values:
  - `0`
  - `5`
  - `50`
- `Состав` is clickable and opens separate slalom-specific lineup editing.
- Start/finish inputs use `чч:мм:сс`.
- Right green block shows:
  - `Результат` = `финиш - старт`
  - `Итог` = `результат + штрафы`
  - `Место`
- Display format for `Результат` and `Итог` is `мм:сс`.
- Slalom ranking rule:
  - best attempt by `distance time + penalties`
  - distance time = `finish - start`
- Default `00:00:00` finish must be ignored and not counted as a valid result.
- Team number block color:
  - no color = no completed attempts
  - yellow = one completed attempt
  - muted green = both attempts completed
- Best attempt is marked by:
  - light row highlight
  - `лучшая` marker in the empty spacer cell under the attempt name

## Slalom Start Scheduler

- Slalom order is based on Sprint results, not on team number.
- Scheduler is in the top block.
- It now has separate controls:
  - `1-я попытка: старт`
  - `1-я попытка: интервал, мин`
  - `2-я попытка: старт`
  - `2-я попытка: интервал, мин`
- It mass-fills starts for both attempts in sprint order.
- Secretary can still manually correct any start time afterward.
- Small red `Очистить` button clears all slalom data for the current category:
  - attempts
  - starts/finishes
  - gate penalties
  - slalom lineup flags

## Protocols

- Protocol registry exists in `Протоколы`.
- Implemented protocols:
  - Sprint results
  - Slalom results
  - H2H results
  - Long race results
  - Combined results
- Combined protocol already includes H2H and Slalom results.
- Slalom results protocol is now a wide landscape-style sheet:
  - one team = 2 rows (`1я попытка`, `2я попытка`)
  - columns:
    - `№`
    - `Команда`
    - `Субъект`
    - `Состав команды`
    - `Попытка`
    - `старт`
    - `финиш`
    - dynamic gates `1в ... Nв`
    - `итог`
    - `Место`
  - only active slalom lineup is shown in `Состав команды`
  - no points column in slalom results protocol
  - best attempt is marked inside the two attempt rows

## Technical Notes

- Legacy DB compatibility is important.
- Old slalom records without finish time must still work.
- `server.py` must support both:
  - `application/x-www-form-urlencoded`
  - `multipart/form-data`
  because slalom autosave uses background `fetch(FormData(...))`.
- `Context.md` should stay compact; add only current-state rules, not full history.

## Verification Status

- Current full test status at last checkpoint:
  - `python3 -m pytest /Users/pavel/Desktop/Codex_Rafting/RaftSecretary/tests -q`
  - `129 passed`

## Most Likely Next Work

- Continue slalom protocol / operator UX polish if needed.
- Then continue remaining export work.

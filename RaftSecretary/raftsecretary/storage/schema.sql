CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO app_meta (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS competition_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT '',
    competition_date TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    organizer TEXT NOT NULL DEFAULT '',
    venue TEXT NOT NULL DEFAULT '',
    enabled_disciplines TEXT NOT NULL DEFAULT '',
    slalom_gate_count INTEGER NOT NULL DEFAULT 8
);

CREATE TABLE IF NOT EXISTS competition_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_order INTEGER NOT NULL,
    competition_day TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    boat_class TEXT NOT NULL,
    sex TEXT NOT NULL,
    age_group TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS required_judges (
    role_key TEXT PRIMARY KEY,
    last_name TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    patronymic TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS judges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_order INTEGER NOT NULL,
    last_name TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    patronymic TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    club TEXT NOT NULL DEFAULT '',
    representative_full_name TEXT NOT NULL DEFAULT '',
    boat_class TEXT NOT NULL,
    sex TEXT NOT NULL,
    age_group TEXT NOT NULL,
    start_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS athletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    athlete_order INTEGER NOT NULL,
    athlete_role TEXT NOT NULL DEFAULT 'main',
    full_name TEXT NOT NULL,
    birth_date TEXT NOT NULL DEFAULT '',
    sport_rank TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sprint_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    start_order INTEGER NOT NULL,
    start_time TEXT NOT NULL DEFAULT '',
    base_time_seconds INTEGER NOT NULL,
    buoy_penalty_seconds INTEGER NOT NULL,
    behavior_penalty_seconds INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sprint_lineup_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    member_order INTEGER NOT NULL,
    is_active INTEGER NOT NULL,
    UNIQUE(category_key, team_name, member_order)
);

CREATE TABLE IF NOT EXISTS parallel_sprint_heats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    round_name TEXT NOT NULL,
    left_team_name TEXT NOT NULL,
    left_start_order INTEGER NOT NULL,
    left_total_time_seconds INTEGER NOT NULL,
    left_missed_buoys INTEGER NOT NULL,
    left_status TEXT NOT NULL,
    right_team_name TEXT NOT NULL,
    right_start_order INTEGER NOT NULL,
    right_total_time_seconds INTEGER NOT NULL,
    right_missed_buoys INTEGER NOT NULL,
    right_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parallel_sprint_heat_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    round_name TEXT NOT NULL,
    scheduled_start_time TEXT NOT NULL DEFAULT '',
    left_base_time_seconds INTEGER NOT NULL DEFAULT 0,
    left_penalty_seconds INTEGER NOT NULL DEFAULT 0,
    right_base_time_seconds INTEGER NOT NULL DEFAULT 0,
    right_penalty_seconds INTEGER NOT NULL DEFAULT 0,
    winner_team_name TEXT NOT NULL DEFAULT '',
    UNIQUE(category_key, round_name)
);

CREATE TABLE IF NOT EXISTS parallel_sprint_start_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    start_order INTEGER NOT NULL,
    start_time TEXT NOT NULL DEFAULT '',
    UNIQUE(category_key, team_name)
);

CREATE TABLE IF NOT EXISTS parallel_sprint_lineup_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    member_order INTEGER NOT NULL,
    is_active INTEGER NOT NULL,
    UNIQUE(category_key, team_name, member_order)
);

CREATE TABLE IF NOT EXISTS slalom_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    base_time_seconds INTEGER NOT NULL,
    gate_penalties TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS long_race_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    start_order INTEGER NOT NULL,
    start_time TEXT NOT NULL DEFAULT '',
    base_time_seconds INTEGER NOT NULL,
    buoy_penalty_seconds INTEGER NOT NULL,
    behavior_penalty_seconds INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS long_race_lineup_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    member_order INTEGER NOT NULL,
    is_active INTEGER NOT NULL,
    UNIQUE(category_key, team_name, member_order)
);

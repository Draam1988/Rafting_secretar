from __future__ import annotations

import sqlite3
from pathlib import Path

from raftsecretary.domain.models import Team, TeamMember


def save_teams(db_path: Path, teams: list[Team]) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_team_schema(connection)
        connection.execute("DELETE FROM athletes")
        connection.execute("DELETE FROM teams")

        for team in teams:
            cursor = connection.execute(
                """
                INSERT INTO teams (
                    name, region, club, representative_full_name, boat_class, sex, age_group, start_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    team.name,
                    team.region,
                    team.club,
                    team.representative_full_name,
                    team.boat_class,
                    team.sex,
                    team.age_group,
                    team.start_number,
                ),
            )
            team_id = cursor.lastrowid
            members = team.members or [
                TeamMember(full_name=athlete_name, birth_date="", rank="", role="main")
                for athlete_name in team.athletes
            ]
            connection.executemany(
                """
                INSERT INTO athletes (team_id, athlete_order, athlete_role, full_name, birth_date, sport_rank)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        team_id,
                        index,
                        member.role,
                        member.full_name,
                        member.birth_date,
                        member.rank,
                    )
                    for index, member in enumerate(members, start=1)
                ],
            )

        connection.commit()


def load_teams(db_path: Path) -> list[Team]:
    with sqlite3.connect(db_path) as connection:
        _ensure_team_schema(connection)
        team_rows = connection.execute(
            """
            SELECT id, name, region, club, representative_full_name, boat_class, sex, age_group, start_number
            FROM teams
            ORDER BY start_number, id
            """
        ).fetchall()

        teams: list[Team] = []
        for team_id, name, region, club, representative_full_name, boat_class, sex, age_group, start_number in team_rows:
            athlete_rows = connection.execute(
                """
                SELECT full_name, birth_date, sport_rank, athlete_role
                FROM athletes
                WHERE team_id = ?
                ORDER BY athlete_order
                """,
                (team_id,),
            ).fetchall()
            members = [
                TeamMember(
                    full_name=full_name,
                    birth_date=birth_date,
                    rank=sport_rank,
                    role=athlete_role,
                )
                for full_name, birth_date, sport_rank, athlete_role in athlete_rows
            ]
            plain_athletes = []
            if members and all(
                member.birth_date == "" and member.rank == "" and member.role == "main"
                for member in members
            ):
                plain_athletes = [member.full_name for member in members]
                members = []
            teams.append(
                Team(
                    name=name,
                    region=region,
                    club=club,
                    representative_full_name=representative_full_name,
                    boat_class=boat_class,
                    sex=sex,
                    age_group=age_group,
                    start_number=start_number,
                    athletes=plain_athletes,
                    members=members,
                )
            )

    return teams


def _ensure_team_schema(connection: sqlite3.Connection) -> None:
    team_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(teams)").fetchall()
    }
    if "club" not in team_columns:
        connection.execute("ALTER TABLE teams ADD COLUMN club TEXT NOT NULL DEFAULT ''")
    if "representative_full_name" not in team_columns:
        connection.execute(
            "ALTER TABLE teams ADD COLUMN representative_full_name TEXT NOT NULL DEFAULT ''"
        )

    athlete_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(athletes)").fetchall()
    }
    if "athlete_role" not in athlete_columns:
        connection.execute(
            "ALTER TABLE athletes ADD COLUMN athlete_role TEXT NOT NULL DEFAULT 'main'"
        )
    if "birth_date" not in athlete_columns:
        connection.execute(
            "ALTER TABLE athletes ADD COLUMN birth_date TEXT NOT NULL DEFAULT ''"
        )
    if "sport_rank" not in athlete_columns:
        connection.execute(
            "ALTER TABLE athletes ADD COLUMN sport_rank TEXT NOT NULL DEFAULT ''"
        )

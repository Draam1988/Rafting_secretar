from __future__ import annotations


def combine_points(
    sprint_points: dict[str, int],
    parallel_sprint_points: dict[str, int],
    slalom_points: dict[str, int],
    long_race_points: dict[str, int],
) -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    for points_map in (
        sprint_points,
        parallel_sprint_points,
        slalom_points,
        long_race_points,
    ):
        for team_name, points in points_map.items():
            totals[team_name] = totals.get(team_name, 0) + points

    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))


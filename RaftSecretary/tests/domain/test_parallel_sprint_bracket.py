from raftsecretary.domain.parallel_sprint import (
    ParallelSprintHeatResult,
    build_four_team_finals,
    resolve_four_team_places,
)
from raftsecretary.domain.status_rules import STATUS_OK


def test_four_team_bracket_builds_finals_from_semifinal_winners_and_losers() -> None:
    semifinal_1 = (
        ParallelSprintHeatResult("T1", "left", 1, 120, 0, STATUS_OK),
        ParallelSprintHeatResult("T4", "right", 4, 130, 0, STATUS_OK),
    )
    semifinal_2 = (
        ParallelSprintHeatResult("T2", "left", 2, 121, 0, STATUS_OK),
        ParallelSprintHeatResult("T3", "right", 3, 125, 0, STATUS_OK),
    )

    final_a, final_b = build_four_team_finals([semifinal_1, semifinal_2])

    assert [entry.team_name for entry in final_a] == ["T1", "T2"]
    assert [entry.team_name for entry in final_b] == ["T4", "T3"]


def test_four_team_places_use_final_a_and_final_b_results() -> None:
    final_a = (
        ParallelSprintHeatResult("T1", "left", 1, 119, 0, STATUS_OK),
        ParallelSprintHeatResult("T2", "right", 2, 122, 0, STATUS_OK),
    )
    final_b = (
        ParallelSprintHeatResult("T3", "left", 3, 121, 0, STATUS_OK),
        ParallelSprintHeatResult("T4", "right", 4, 126, 0, STATUS_OK),
    )

    places = resolve_four_team_places(final_a, final_b)

    assert places == {
        "T1": 1,
        "T2": 2,
        "T3": 3,
        "T4": 4,
    }


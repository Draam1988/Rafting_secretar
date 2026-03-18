from raftsecretary.domain.parallel_sprint import (
    ParallelSprintHeatResult,
    rank_eliminated_crews,
    resolve_heat_winner,
)
from raftsecretary.domain.status_rules import (
    STATUS_DISQUALIFIED_ATTEMPT,
    STATUS_OK,
)


def test_heat_winner_is_faster_finished_crew() -> None:
    left = ParallelSprintHeatResult(
        team_name="Alpha",
        lane="left",
        start_order=1,
        total_time_seconds=120,
        missed_buoys=0,
        status=STATUS_OK,
    )
    right = ParallelSprintHeatResult(
        team_name="Beta",
        lane="right",
        start_order=2,
        total_time_seconds=125,
        missed_buoys=0,
        status=STATUS_OK,
    )

    winner = resolve_heat_winner(left, right)

    assert winner.team_name == "Alpha"


def test_completed_buoy_requirement_beats_faster_crew_that_missed_buoy() -> None:
    left = ParallelSprintHeatResult(
        team_name="Alpha",
        lane="left",
        start_order=1,
        total_time_seconds=140,
        missed_buoys=0,
        status=STATUS_OK,
    )
    right = ParallelSprintHeatResult(
        team_name="Beta",
        lane="right",
        start_order=2,
        total_time_seconds=110,
        missed_buoys=1,
        status=STATUS_OK,
    )

    winner = resolve_heat_winner(left, right)

    assert winner.team_name == "Alpha"


def test_finished_crew_beats_disqualified_attempt() -> None:
    left = ParallelSprintHeatResult(
        team_name="Alpha",
        lane="left",
        start_order=1,
        total_time_seconds=140,
        missed_buoys=0,
        status=STATUS_OK,
    )
    right = ParallelSprintHeatResult(
        team_name="Beta",
        lane="right",
        start_order=2,
        total_time_seconds=100,
        missed_buoys=0,
        status=STATUS_DISQUALIFIED_ATTEMPT,
    )

    winner = resolve_heat_winner(left, right)

    assert winner.team_name == "Alpha"


def test_eliminated_crews_are_ranked_by_last_heat_time() -> None:
    first = ParallelSprintHeatResult(
        team_name="Alpha",
        lane="left",
        start_order=1,
        total_time_seconds=121,
        missed_buoys=0,
        status=STATUS_OK,
    )
    second = ParallelSprintHeatResult(
        team_name="Beta",
        lane="right",
        start_order=2,
        total_time_seconds=118,
        missed_buoys=0,
        status=STATUS_OK,
    )
    third = ParallelSprintHeatResult(
        team_name="Gamma",
        lane="left",
        start_order=3,
        total_time_seconds=130,
        missed_buoys=0,
        status=STATUS_OK,
    )

    ranked = rank_eliminated_crews([first, second, third])

    assert [entry.team_name for entry in ranked] == ["Beta", "Alpha", "Gamma"]


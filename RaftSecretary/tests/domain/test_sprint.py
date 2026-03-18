from raftsecretary.domain.sprint import SprintEntry, rank_sprint_entries
from raftsecretary.domain.status_rules import (
    STATUS_DID_NOT_FINISH,
    STATUS_DID_NOT_START,
    STATUS_DISQUALIFIED_ATTEMPT,
    STATUS_OK,
)


def test_sprint_total_time_includes_all_penalties() -> None:
    entry = SprintEntry(
        team_name="Storm",
        start_order=2,
        base_time_seconds=75,
        buoy_penalty_seconds=50,
        behavior_penalty_seconds=10,
        status=STATUS_OK,
    )

    assert entry.total_time_seconds == 135


def test_sprint_tie_is_resolved_by_earlier_start_order() -> None:
    first = SprintEntry(
        team_name="Alpha",
        start_order=1,
        base_time_seconds=80,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_OK,
    )
    second = SprintEntry(
        team_name="Beta",
        start_order=2,
        base_time_seconds=80,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_OK,
    )

    ranked = rank_sprint_entries([second, first])

    assert [entry.team_name for entry in ranked] == ["Alpha", "Beta"]


def test_dnf_and_dsq_attempt_rank_after_finished_crews() -> None:
    finished = SprintEntry(
        team_name="Alpha",
        start_order=1,
        base_time_seconds=80,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_OK,
    )
    did_not_finish = SprintEntry(
        team_name="Beta",
        start_order=2,
        base_time_seconds=70,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_DID_NOT_FINISH,
    )
    disqualified_attempt = SprintEntry(
        team_name="Gamma",
        start_order=3,
        base_time_seconds=60,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_DISQUALIFIED_ATTEMPT,
    )

    ranked = rank_sprint_entries([did_not_finish, disqualified_attempt, finished])

    assert [entry.team_name for entry in ranked] == ["Alpha", "Beta", "Gamma"]


def test_did_not_start_ranks_after_last_place_entries() -> None:
    finished = SprintEntry(
        team_name="Alpha",
        start_order=1,
        base_time_seconds=80,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_OK,
    )
    did_not_finish = SprintEntry(
        team_name="Beta",
        start_order=2,
        base_time_seconds=70,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_DID_NOT_FINISH,
    )
    did_not_start = SprintEntry(
        team_name="Gamma",
        start_order=3,
        base_time_seconds=0,
        buoy_penalty_seconds=0,
        behavior_penalty_seconds=0,
        status=STATUS_DID_NOT_START,
    )

    ranked = rank_sprint_entries([did_not_finish, did_not_start, finished])

    assert [entry.team_name for entry in ranked] == ["Alpha", "Beta", "Gamma"]


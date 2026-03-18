from raftsecretary.domain.status_rules import (
    STATUS_DISQUALIFIED_ATTEMPT,
    STATUS_DISQUALIFIED_SERIES,
    STATUS_DID_NOT_FINISH,
    STATUS_DID_NOT_START,
    STATUS_OK,
    place_value_for_status,
)


def test_ok_status_keeps_original_place() -> None:
    assert place_value_for_status(STATUS_OK, place=3, starters_count=12) == 3


def test_dnf_and_dsq_attempt_become_last_place() -> None:
    assert place_value_for_status(STATUS_DID_NOT_FINISH, place=4, starters_count=12) == 12
    assert place_value_for_status(STATUS_DISQUALIFIED_ATTEMPT, place=1, starters_count=12) == 12


def test_did_not_start_has_no_place() -> None:
    assert place_value_for_status(STATUS_DID_NOT_START, place=7, starters_count=12) is None


def test_dsq_series_has_no_place() -> None:
    assert place_value_for_status(STATUS_DISQUALIFIED_SERIES, place=2, starters_count=12) is None


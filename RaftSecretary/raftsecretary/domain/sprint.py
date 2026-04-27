from __future__ import annotations

from dataclasses import dataclass

from raftsecretary.domain.status_rules import (
    STATUS_DID_NOT_FINISH,
    STATUS_DID_NOT_START,
    STATUS_DISQUALIFIED_ATTEMPT,
    STATUS_DISQUALIFIED_SERIES,
    STATUS_OK,
    STATUS_RETIRED,
)


@dataclass(frozen=True)
class SprintEntry:
    team_name: str
    start_order: int
    base_time_seconds: int
    buoy_penalty_seconds: int
    behavior_penalty_seconds: int
    status: str
    start_time: str = ""

    @property
    def total_time_seconds(self) -> int:
        return (
            self.base_time_seconds
            + self.buoy_penalty_seconds
            + self.behavior_penalty_seconds
        )


def _status_rank(status: str) -> int:
    if status == STATUS_OK:
        return 0
    if status in {STATUS_DID_NOT_FINISH, STATUS_DISQUALIFIED_ATTEMPT}:
        return 1
    if status in {STATUS_DID_NOT_START, STATUS_DISQUALIFIED_SERIES, STATUS_RETIRED}:
        return 2
    raise ValueError(f"Unsupported sprint status: {status}")


def rank_sprint_entries(entries: list[SprintEntry]) -> list[SprintEntry]:
    return sorted(
        entries,
        key=lambda entry: (
            _status_rank(entry.status),
            entry.total_time_seconds if entry.status == STATUS_OK else 0,
            entry.start_order,
        ),
    )

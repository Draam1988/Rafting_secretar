from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlalomRun:
    team_name: str
    attempt_number: int
    base_time_seconds: int
    gate_penalties: list[int]
    finish_time_seconds: int = 0

    @property
    def distance_time_seconds(self) -> int:
        if self.finish_time_seconds > 0:
            return max(self.finish_time_seconds - self.base_time_seconds, 0)
        return self.base_time_seconds

    @property
    def total_time_seconds(self) -> int:
        return self.distance_time_seconds + sum(self.gate_penalties)


def best_run_for_team(runs: list[SlalomRun]) -> SlalomRun:
    if not runs:
        raise ValueError("At least one run is required")
    return sorted(runs, key=lambda run: (run.total_time_seconds, run.attempt_number))[0]

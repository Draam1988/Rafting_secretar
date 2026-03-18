from __future__ import annotations

from dataclasses import dataclass

from raftsecretary.domain.status_rules import (
    STATUS_DID_NOT_FINISH,
    STATUS_DID_NOT_START,
    STATUS_DISQUALIFIED_ATTEMPT,
    STATUS_DISQUALIFIED_SERIES,
    STATUS_OK,
)


@dataclass(frozen=True)
class ParallelSprintHeatResult:
    team_name: str
    lane: str
    start_order: int
    total_time_seconds: int
    missed_buoys: int
    status: str


def main_bracket_size(team_count: int) -> int:
    if team_count < 3:
        raise ValueError("Parallel sprint requires at least 3 teams")

    size = 2
    while size * 2 <= team_count:
        size *= 2
    return size


def stage_one_team_count(team_count: int) -> int:
    bracket_size = main_bracket_size(team_count)
    return max(0, 2 * (team_count - bracket_size))


def build_stage_one_pairs(sprint_order: list[str]) -> list[tuple[str, str]]:
    count = stage_one_team_count(len(sprint_order))
    if count == 0:
        return []

    stage_one_teams = sprint_order[-count:]
    return [
        (stage_one_teams[index], stage_one_teams[-(index + 1)])
        for index in range(count // 2)
    ]


def build_stage_one_matches(sprint_order: list[str]) -> list[tuple[int, str, str]]:
    direct_qualifiers, _stage_one_teams = split_direct_qualifiers_and_stage_one(sprint_order)
    pairs = build_stage_one_pairs(sprint_order)
    first_target_seed = len(direct_qualifiers) + 1
    return [
        (first_target_seed + index, left, right)
        for index, (left, right) in enumerate(pairs)
    ]


def split_direct_qualifiers_and_stage_one(
    sprint_order: list[str],
) -> tuple[list[str], list[str]]:
    stage_one_count = stage_one_team_count(len(sprint_order))
    if stage_one_count == 0:
        return sprint_order[:], []
    direct_qualifiers = sprint_order[:-stage_one_count]
    stage_one_teams = sprint_order[-stage_one_count:]
    return direct_qualifiers, stage_one_teams


def build_four_team_semifinals(main_stage_teams: list[str]) -> list[tuple[str, str]]:
    if len(main_stage_teams) != 4:
        raise ValueError("Four-team semifinals require exactly four teams")
    return [
        (main_stage_teams[0], main_stage_teams[3]),
        (main_stage_teams[1], main_stage_teams[2]),
    ]


def second_stage_seed_order(bracket_size: int) -> list[int]:
    if bracket_size < 2 or bracket_size & (bracket_size - 1) != 0:
        raise ValueError("Second stage bracket size must be a power of two")
    order = [1, 2]
    size = 2
    while size < bracket_size:
        size *= 2
        next_order: list[int] = []
        for seed in order:
            next_order.append(seed)
            next_order.append(size + 1 - seed)
        order = next_order
    return order


def build_second_stage_pairs(sprint_order: list[str]) -> list[tuple[str, str]]:
    bracket_size = main_bracket_size(len(sprint_order))
    direct_qualifiers, _stage_one_teams = split_direct_qualifiers_and_stage_one(sprint_order)
    entrants: dict[int, str] = {
        seed: team_name for seed, team_name in enumerate(direct_qualifiers, start=1)
    }
    for target_seed, _left, _right in build_stage_one_matches(sprint_order):
        entrants[target_seed] = f"Победитель за {target_seed} место"
    seed_order = second_stage_seed_order(bracket_size)
    return [
        (entrants[left_seed], entrants[right_seed])
        for left_seed, right_seed in zip(seed_order[::2], seed_order[1::2], strict=True)
    ]


def _heat_status_rank(entry: ParallelSprintHeatResult) -> int:
    if entry.status == STATUS_OK and entry.missed_buoys == 0:
        return 0
    if entry.status == STATUS_OK and entry.missed_buoys > 0:
        return 1
    if entry.status in {STATUS_DID_NOT_FINISH, STATUS_DISQUALIFIED_ATTEMPT}:
        return 2
    if entry.status in {STATUS_DID_NOT_START, STATUS_DISQUALIFIED_SERIES}:
        return 3
    raise ValueError(f"Unsupported parallel sprint status: {entry.status}")


def resolve_heat_winner(
    left: ParallelSprintHeatResult,
    right: ParallelSprintHeatResult,
) -> ParallelSprintHeatResult:
    ranked = sorted(
        [left, right],
        key=lambda entry: (
            _heat_status_rank(entry),
            entry.total_time_seconds,
            entry.start_order,
        ),
    )
    return ranked[0]


def rank_eliminated_crews(
    entries: list[ParallelSprintHeatResult],
) -> list[ParallelSprintHeatResult]:
    return sorted(
        entries,
        key=lambda entry: (
            _heat_status_rank(entry),
            entry.total_time_seconds,
            entry.start_order,
        ),
    )


def build_four_team_finals(
    semifinals: list[tuple[ParallelSprintHeatResult, ParallelSprintHeatResult]],
) -> tuple[
    tuple[ParallelSprintHeatResult, ParallelSprintHeatResult],
    tuple[ParallelSprintHeatResult, ParallelSprintHeatResult],
]:
    if len(semifinals) != 2:
        raise ValueError("Exactly two semifinals are required for a four-team bracket")

    semifinal_1_winner = resolve_heat_winner(*semifinals[0])
    semifinal_2_winner = resolve_heat_winner(*semifinals[1])

    semifinal_1_loser = _other_heat_entry(semifinals[0], semifinal_1_winner.team_name)
    semifinal_2_loser = _other_heat_entry(semifinals[1], semifinal_2_winner.team_name)

    final_a = (semifinal_1_winner, semifinal_2_winner)
    final_b = (semifinal_1_loser, semifinal_2_loser)
    return final_a, final_b


def resolve_four_team_places(
    final_a: tuple[ParallelSprintHeatResult, ParallelSprintHeatResult],
    final_b: tuple[ParallelSprintHeatResult, ParallelSprintHeatResult],
) -> dict[str, int]:
    final_a_winner = resolve_heat_winner(*final_a)
    final_a_loser = _other_heat_entry(final_a, final_a_winner.team_name)

    final_b_winner = resolve_heat_winner(*final_b)
    final_b_loser = _other_heat_entry(final_b, final_b_winner.team_name)

    return {
        final_a_winner.team_name: 1,
        final_a_loser.team_name: 2,
        final_b_winner.team_name: 3,
        final_b_loser.team_name: 4,
    }


def _other_heat_entry(
    heat: tuple[ParallelSprintHeatResult, ParallelSprintHeatResult],
    winner_name: str,
) -> ParallelSprintHeatResult:
    left, right = heat
    if left.team_name == winner_name:
        return right
    if right.team_name == winner_name:
        return left
    raise ValueError("Winner is not present in the heat")

from raftsecretary.domain.slalom import SlalomRun, best_run_for_team


def test_slalom_run_total_includes_gate_penalties() -> None:
    run = SlalomRun(team_name="Alpha", attempt_number=1, base_time_seconds=120, gate_penalties=[0, 5, 50])

    assert run.total_time_seconds == 175


def test_slalom_run_uses_finish_minus_start_when_finish_exists() -> None:
    run = SlalomRun(
        team_name="Alpha",
        attempt_number=1,
        base_time_seconds=60,
        finish_time_seconds=185,
        gate_penalties=[0, 5, 50],
    )

    assert run.distance_time_seconds == 125
    assert run.total_time_seconds == 180


def test_best_run_for_team_picks_lower_total_time() -> None:
    first = SlalomRun(team_name="Alpha", attempt_number=1, base_time_seconds=120, gate_penalties=[5, 5])
    second = SlalomRun(team_name="Alpha", attempt_number=2, base_time_seconds=118, gate_penalties=[0, 0])

    best = best_run_for_team([first, second])

    assert best.attempt_number == 2

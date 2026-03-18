from raftsecretary.domain.combined import combine_points


def test_combine_points_sums_discipline_scores_by_team() -> None:
    combined = combine_points(
        sprint_points={"Alpha": 100, "Beta": 95},
        parallel_sprint_points={"Alpha": 200, "Beta": 180},
        slalom_points={"Alpha": 300, "Beta": 285},
        long_race_points={"Alpha": 400, "Beta": 380},
    )

    assert combined == [("Alpha", 1000), ("Beta", 940)]


def test_combine_points_handles_missing_disciplines() -> None:
    combined = combine_points(
        sprint_points={"Alpha": 100},
        parallel_sprint_points={},
        slalom_points={"Alpha": 300},
        long_race_points={},
    )

    assert combined == [("Alpha", 400)]


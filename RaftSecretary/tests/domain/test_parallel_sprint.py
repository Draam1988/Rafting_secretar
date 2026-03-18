from raftsecretary.domain.parallel_sprint import (
    build_stage_one_pairs,
    main_bracket_size,
    stage_one_team_count,
)


def test_main_bracket_size_uses_nearest_power_of_two() -> None:
    assert main_bracket_size(3) == 2
    assert main_bracket_size(4) == 4
    assert main_bracket_size(5) == 4
    assert main_bracket_size(8) == 8
    assert main_bracket_size(15) == 8
    assert main_bracket_size(16) == 16


def test_stage_one_team_count_matches_rules_examples() -> None:
    assert stage_one_team_count(3) == 2
    assert stage_one_team_count(4) == 0
    assert stage_one_team_count(5) == 2
    assert stage_one_team_count(6) == 4
    assert stage_one_team_count(7) == 6
    assert stage_one_team_count(8) == 0
    assert stage_one_team_count(12) == 8


def test_stage_one_pairs_use_worst_sprint_crews_only() -> None:
    sprint_order = [
        "T1",
        "T2",
        "T3",
        "T4",
        "T5",
        "T6",
    ]

    pairs = build_stage_one_pairs(sprint_order)

    assert pairs == [("T3", "T6"), ("T4", "T5")]


def test_stage_one_pairs_for_seven_teams_split_first_and_second_half() -> None:
    sprint_order = [
        "T1",
        "T2",
        "T3",
        "T4",
        "T5",
        "T6",
        "T7",
    ]

    pairs = build_stage_one_pairs(sprint_order)

    assert pairs == [("T2", "T7"), ("T3", "T6"), ("T4", "T5")]


def test_stage_one_pairs_for_eleven_teams_follow_document() -> None:
    sprint_order = [f"T{i}" for i in range(1, 12)]

    pairs = build_stage_one_pairs(sprint_order)

    assert pairs == [("T6", "T11"), ("T7", "T10"), ("T8", "T9")]

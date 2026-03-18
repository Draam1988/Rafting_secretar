from raftsecretary.domain.parallel_sprint import (
    build_four_team_semifinals,
    build_second_stage_pairs,
    build_stage_one_matches,
    second_stage_seed_order,
    split_direct_qualifiers_and_stage_one,
)


def test_split_direct_qualifiers_and_stage_one_for_six_teams() -> None:
    sprint_order = ["T1", "T2", "T3", "T4", "T5", "T6"]

    direct_qualifiers, stage_one_teams = split_direct_qualifiers_and_stage_one(sprint_order)

    assert direct_qualifiers == ["T1", "T2"]
    assert stage_one_teams == ["T3", "T4", "T5", "T6"]


def test_build_four_team_semifinals_uses_standard_seeding() -> None:
    main_stage_teams = ["T1", "T2", "T3", "T4"]

    semifinals = build_four_team_semifinals(main_stage_teams)

    assert semifinals == [("T1", "T4"), ("T2", "T3")]


def test_second_stage_seed_order_for_eight_teams_uses_standard_bracket() -> None:
    assert second_stage_seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_build_stage_one_matches_assigns_target_seed_numbers() -> None:
    sprint_order = ["T1", "T2", "T3", "T4", "T5"]

    matches = build_stage_one_matches(sprint_order)

    assert matches == [(4, "T4", "T5")]


def test_build_stage_one_matches_for_eleven_teams_follow_document() -> None:
    sprint_order = [f"T{i}" for i in range(1, 12)]

    matches = build_stage_one_matches(sprint_order)

    assert matches == [
        (6, "T6", "T11"),
        (7, "T7", "T10"),
        (8, "T8", "T9"),
    ]


def test_build_second_stage_pairs_for_five_teams_uses_winner_placeholder_for_fourth_seed() -> None:
    sprint_order = ["T1", "T2", "T3", "T4", "T5"]

    pairs = build_second_stage_pairs(sprint_order)

    assert pairs == [("T1", "Победитель за 4 место"), ("T2", "T3")]

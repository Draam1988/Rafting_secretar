from raftsecretary.domain.points import points_for_place


def test_points_for_winner_match_official_table() -> None:
    assert points_for_place("sprint", 1) == 100
    assert points_for_place("parallel_sprint", 1) == 200
    assert points_for_place("slalom", 1) == 300
    assert points_for_place("long_race", 1) == 400


def test_points_for_middle_places_match_official_table() -> None:
    assert points_for_place("sprint", 10) == 55
    assert points_for_place("parallel_sprint", 15) == 60
    assert points_for_place("slalom", 20) == 15
    assert points_for_place("long_race", 2) == 380


def test_places_below_twentieth_receive_zero_points() -> None:
    assert points_for_place("sprint", 21) == 0
    assert points_for_place("parallel_sprint", 35) == 0


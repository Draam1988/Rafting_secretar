from raftsecretary.domain.models import Category, Competition, Team, normalize_sex


def test_mixed_crews_are_normalized_to_mens_category() -> None:
    assert normalize_sex("mixed") == "men"
    assert normalize_sex("смешанные") == "men"


def test_category_key_uses_normalized_sex() -> None:
    category = Category(boat_class="R4", sex="mixed", age_group="U24")

    assert category.key == "R4:men:U24"


def test_competition_stores_team_in_matching_category() -> None:
    competition = Competition(
        name="Test Event",
        competition_date="2026-03-14",
        enabled_disciplines=["sprint"],
        categories=[Category(boat_class="R4", sex="men", age_group="U24")],
    )
    team = Team(
        name="Storm",
        region="Moscow",
        boat_class="R4",
        sex="mixed",
        age_group="U24",
        start_number=1,
        athletes=["A", "B", "C", "D"],
    )

    competition.add_team(team)

    assert competition.teams_by_category()["R4:men:U24"][0].name == "Storm"


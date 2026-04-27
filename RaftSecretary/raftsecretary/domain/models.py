from __future__ import annotations

from dataclasses import dataclass, field


SEX_ALIASES = {
    "men": "men",
    "male": "men",
    "mixed": "men",
    "мужские": "men",
    "мужчины": "men",
    "смешанные": "men",
    "women": "women",
    "female": "women",
    "женские": "women",
    "женщины": "women",
}

SEX_DISPLAY = {
    "men": "мужчины",
    "women": "женщины",
}


def normalize_sex(value: str) -> str:
    normalized = value.strip().lower()
    return SEX_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class Category:
    boat_class: str
    sex: str
    age_group: str

    @property
    def normalized_sex(self) -> str:
        return normalize_sex(self.sex)

    @property
    def key(self) -> str:
        return f"{self.boat_class}:{self.normalized_sex}:{self.age_group}"

    @property
    def display_name(self) -> str:
        sex = SEX_DISPLAY.get(self.normalized_sex, self.normalized_sex)
        return f"{self.boat_class} {sex} {self.age_group}".strip()


@dataclass(frozen=True)
class TeamMember:
    full_name: str
    birth_date: str
    rank: str
    role: str = "main"


@dataclass(frozen=True)
class Team:
    name: str
    region: str
    boat_class: str
    sex: str
    age_group: str
    start_number: int
    athletes: list[str] = field(default_factory=list)
    club: str = ""
    representative_full_name: str = ""
    members: list[TeamMember] = field(default_factory=list)
    id: int | None = field(default=None, compare=False)

    @property
    def category_key(self) -> str:
        return Category(
            boat_class=self.boat_class,
            sex=self.sex,
            age_group=self.age_group,
        ).key

    @property
    def crew_members(self) -> list[TeamMember]:
        if self.members:
            return self.members
        return [TeamMember(full_name=name, birth_date="", rank="", role="main") for name in self.athletes]


@dataclass
class Competition:
    name: str
    competition_date: str
    enabled_disciplines: list[str]
    categories: list[Category]
    teams: list[Team] = field(default_factory=list)

    def add_team(self, team: Team) -> None:
        allowed_keys = {category.key for category in self.categories}
        if team.category_key not in allowed_keys:
            raise ValueError(f"Team category is not enabled: {team.category_key}")
        self.teams.append(team)

    def teams_by_category(self) -> dict[str, list[Team]]:
        grouped = {category.key: [] for category in self.categories}
        for team in self.teams:
            grouped.setdefault(team.category_key, []).append(team)
        return grouped

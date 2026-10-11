"""Roles: task permissions, document clearance (public < internal), live-data permission and briefing style."""

from dataclasses import dataclass
from functools import lru_cache

import yaml

from medbrief.config import get_settings

LEVELS = ("public", "internal")


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    clearance: str
    tasks: tuple[str, ...]
    live_data: bool
    style: str

    def allows(self, task: str) -> bool:
        return task in self.tasks

    @property
    def visible_levels(self) -> list[str]:
        return list(LEVELS[: LEVELS.index(self.clearance) + 1])

    def can_see(self, classification: str) -> bool:
        return classification in self.visible_levels


@lru_cache
def load_roles() -> tuple[dict[str, Role], dict[str, str]]:
    data = yaml.safe_load(get_settings().roles_file.read_text(encoding="utf-8"))
    roles = {n: Role(n, s["description"], s["clearance"], tuple(s["tasks"]), bool(s.get("live_data")), s.get("style", "analyst"))
             for n, s in data["roles"].items()}
    return roles, dict(data.get("demo_api_keys", {}))


def get_role(name: str) -> Role:
    roles, _ = load_roles()
    if name not in roles:
        raise KeyError(f"Unknown role '{name}'. Known roles: {', '.join(roles)}")
    return roles[name]


def role_for_api_key(api_key: str | None) -> Role | None:
    roles, keys = load_roles()
    return roles.get(keys.get(api_key or "", ""))

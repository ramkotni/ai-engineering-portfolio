"""Roles: which documentation sources a role may search (safety is always allowed)."""

from dataclasses import dataclass
from functools import lru_cache

import yaml

from plant_assist.config import get_settings

ALWAYS_ALLOWED = {"safety"}


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    sources: tuple[str, ...]

    def can_search(self, source: str) -> bool:
        return source in self.sources or source in ALWAYS_ALLOWED


@lru_cache
def load_roles() -> tuple[dict[str, Role], dict[str, str]]:
    data = yaml.safe_load(get_settings().roles_file.read_text(encoding="utf-8"))
    roles = {n: Role(n, s["description"], tuple(s["sources"])) for n, s in data["roles"].items()}
    return roles, dict(data.get("demo_api_keys", {}))


def get_role(name: str) -> Role:
    roles, _ = load_roles()
    if name not in roles:
        raise KeyError(f"Unknown role '{name}'. Known roles: {', '.join(roles)}")
    return roles[name]


def role_for_api_key(api_key: str | None) -> Role | None:
    roles, keys = load_roles()
    return roles.get(keys.get(api_key or "", ""))

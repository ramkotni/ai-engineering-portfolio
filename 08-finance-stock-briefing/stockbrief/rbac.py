"""Roles: task permissions (briefing, qa, quote, audit), live-data permission and briefing style."""

from dataclasses import dataclass
from functools import lru_cache

import yaml

from stockbrief.config import get_settings


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    tasks: tuple[str, ...]
    live_data: bool
    style: str

    def allows(self, task: str) -> bool:
        return task in self.tasks


@lru_cache
def load_roles() -> tuple[dict[str, Role], dict[str, str]]:
    data = yaml.safe_load(get_settings().roles_file.read_text(encoding="utf-8"))
    roles = {n: Role(n, s["description"], tuple(s["tasks"]), bool(s.get("live_data")), s.get("style", "advisor"))
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

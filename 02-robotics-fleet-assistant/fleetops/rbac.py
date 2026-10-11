"""Role-based access control: allowed intents (agents) and zone scope (row-level security) per role."""

from dataclasses import dataclass
from functools import lru_cache

import yaml

from fleetops.config import get_settings


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    intents: tuple[str, ...]
    zones: tuple[str, ...]          # empty = all zones
    summary_style: str

    def allows(self, intent: str) -> bool:
        return intent in self.intents

    def can_see_zone(self, zone: str) -> bool:
        return not self.zones or zone in self.zones


@lru_cache
def load_roles() -> tuple[dict[str, Role], dict[str, str]]:
    data = yaml.safe_load(get_settings().roles_file.read_text(encoding="utf-8"))
    roles = {n: Role(n, s["description"], tuple(s["intents"]), tuple(s.get("zones") or ()), s["summary_style"])
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

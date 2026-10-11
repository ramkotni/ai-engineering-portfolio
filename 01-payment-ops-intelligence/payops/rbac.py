"""Role-based access control: which intents (agents) a role may use and what data it may see."""

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from payops.config import get_settings

AMOUNT = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|K|M|million|thousand))?")


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    intents: tuple[str, ...]
    can_view_amounts: bool
    summary_style: str

    def allows(self, intent: str) -> bool:
        return intent in self.intents


@lru_cache
def load_roles() -> tuple[dict[str, Role], dict[str, str]]:
    data = yaml.safe_load(get_settings().roles_file.read_text(encoding="utf-8"))
    roles = {
        name: Role(name, spec["description"], tuple(spec["intents"]), bool(spec["can_view_amounts"]), spec["summary_style"])
        for name, spec in data["roles"].items()
    }
    return roles, dict(data.get("demo_api_keys", {}))


def get_role(name: str) -> Role:
    roles, _ = load_roles()
    if name not in roles:
        raise KeyError(f"Unknown role '{name}'. Known roles: {', '.join(roles)}")
    return roles[name]


def role_for_api_key(api_key: str | None) -> Role | None:
    roles, keys = load_roles()
    return roles.get(keys.get(api_key or "", ""))


def mask_amounts(text: str) -> str:
    """Hide dollar amounts for roles without financial visibility."""
    return AMOUNT.sub("[amount restricted]", text)

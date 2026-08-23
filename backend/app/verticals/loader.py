"""Loads, validates, and caches vertical config packs from app/verticals/packs/*.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.config import settings
from app.verticals.base import VerticalConfig

PACKS_DIR = Path(__file__).parent / "packs"

_cache: dict[str, VerticalConfig] = {}


class VerticalConfigError(Exception):
    """Raised when a vertical config pack is missing, malformed, or invalid."""


def load_vertical_pack(key: str, *, packs_dir: Path = PACKS_DIR) -> VerticalConfig:
    """Reads, parses, and validates a single vertical config pack. Does not use the cache."""
    path = packs_dir / f"{key}.yaml"

    if not path.exists():
        available = sorted(p.stem for p in packs_dir.glob("*.yaml")) if packs_dir.exists() else []
        raise VerticalConfigError(
            f"No vertical config pack found for '{key}' at {path}. Available packs: {available}"
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise VerticalConfigError(f"Vertical pack '{key}' at {path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise VerticalConfigError(f"Vertical pack '{key}' at {path} must parse to a mapping, got {type(raw).__name__}")

    try:
        config = VerticalConfig.model_validate(raw)
    except ValidationError as exc:
        raise VerticalConfigError(f"Vertical pack '{key}' at {path} failed validation:\n{exc}") from exc

    if config.key != key:
        raise VerticalConfigError(
            f"Vertical pack at {path} declares key='{config.key}' but is filed under '{key}.yaml'. "
            "The key field and filename must match."
        )

    return config


def get_vertical(key: str) -> VerticalConfig:
    """Cached accessor for a vertical config pack by key."""
    if key not in _cache:
        _cache[key] = load_vertical_pack(key)
    return _cache[key]


def get_active_vertical() -> VerticalConfig:
    """Returns the config pack for the currently configured ACTIVE_VERTICAL."""
    return get_vertical(settings.ACTIVE_VERTICAL)


def list_available_verticals() -> list[str]:
    """Keys of every vertical config pack present in app/verticals/packs/."""
    if not PACKS_DIR.exists():
        return []
    return sorted(p.stem for p in PACKS_DIR.glob("*.yaml"))

"""The vertical configuration layer: config packs, not code, is what makes Taskmaster vertical-agnostic."""
from app.verticals.base import VerticalConfig
from app.verticals.loader import (
    VerticalConfigError,
    get_active_vertical,
    get_vertical,
    list_available_verticals,
)

__all__ = [
    "VerticalConfig",
    "VerticalConfigError",
    "get_active_vertical",
    "get_vertical",
    "list_available_verticals",
]

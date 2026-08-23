"""Shared base model config for every model in the agent contract."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TaskmasterModel(BaseModel):
    """Base for every model crossing an agent boundary.

    extra="forbid" is what makes this a real contract: a typo'd or stray field from an
    agent fails validation loudly instead of silently passing through to the next stage.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

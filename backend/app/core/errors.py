"""Shared exception types for external-service integrations (app/integrations/)."""
from __future__ import annotations


class IntegrationError(Exception):
    """Base for every external-service integration failure."""


class IntegrationTimeoutError(IntegrationError):
    """An external call exceeded its timeout budget on every retry attempt."""


class IntegrationUnavailableError(IntegrationError):
    """An external call failed (non-timeout) on every retry attempt."""


class ConfigurationError(IntegrationError):
    """A client was constructed without the environment variables it requires."""

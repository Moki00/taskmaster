"""Shared OAuth credential construction for GmailClient and CalendarClient - same OAuth app
(GMAIL_CLIENT_ID/SECRET + a stored refresh token), different scopes per client.
"""
from __future__ import annotations

from google.oauth2.credentials import Credentials

from app.config import settings
from app.core.errors import ConfigurationError

_TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_google_credentials(*, required_scopes: list[str]) -> Credentials:
    """Builds OAuth2 credentials from the configured refresh token.

    GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET/GMAIL_REFRESH_TOKEN are Optional in Settings (the app can
    start without them), so this is checked here at client-construction time, not at startup -
    raises ConfigurationError naming exactly which variable(s) are missing.
    """
    missing = [
        name
        for name, value in (
            ("GMAIL_CLIENT_ID", settings.GMAIL_CLIENT_ID),
            ("GMAIL_CLIENT_SECRET", settings.GMAIL_CLIENT_SECRET),
            ("GMAIL_REFRESH_TOKEN", settings.GMAIL_REFRESH_TOKEN),
        )
        if not value
    ]
    if missing:
        raise ConfigurationError(
            f"Missing required environment variable(s) for Google API access: {', '.join(missing)}"
        )

    return Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        token_uri=_TOKEN_URI,
        scopes=required_scopes,
    )

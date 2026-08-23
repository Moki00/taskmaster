"""Persistence layer. Agents depend on this package's TicketRepository interface, never on a
concrete implementation or the Firestore SDK directly.
"""
from app.services.repository import (
    RepoError,
    TicketNotFoundError,
    TicketPage,
    TicketRepository,
    get_repository,
)

__all__ = [
    "RepoError",
    "TicketNotFoundError",
    "TicketPage",
    "TicketRepository",
    "get_repository",
]

"""
General admin utilities: user tracking on every message, error fallback.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

import database as db

logger = logging.getLogger(__name__)
router = Router(name="admin")


@router.message()
async def track_message(message: Message) -> None:
    """
    Passive handler — runs for every message not caught by a more specific handler.
    Records the sender in the database so /users and /stats stay accurate.
    """
    if message.from_user is None or message.chat.type not in ("group", "supergroup"):
        return
    try:
        await db.upsert_user(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_active=True,
        )
    except Exception:
        logger.exception("track_message: failed to upsert user %s", message.from_user.id)

"""
Anti-spam / rate-limit middleware.

Limits each user to at most RATE_LIMIT messages per RATE_WINDOW seconds.
Silently drops excess updates so the bot stays responsive under load.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

# Allow 5 messages per 5-second window per user
RATE_LIMIT: int = 5
RATE_WINDOW: int = 5  # seconds


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        # user_id -> list of timestamps of recent messages
        self._history: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.monotonic()

        # Prune timestamps outside the current window
        self._history[user_id] = [
            ts for ts in self._history[user_id] if now - ts < RATE_WINDOW
        ]

        if len(self._history[user_id]) >= RATE_LIMIT:
            # Rate-limited — drop the update silently
            return None

        self._history[user_id].append(now)
        return await handler(event, data)

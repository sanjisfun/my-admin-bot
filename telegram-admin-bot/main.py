"""
Telegram Admin Bot — entry point.

Start with:
    python main.py

Required environment variables:
    BOT_TOKEN   — Telegram bot token from @BotFather

Optional environment variables:
    WARN_LIMIT          — warnings before auto-ban (default: 3)
    DEFAULT_MUTE_SECONDS — default mute duration in seconds (default: 3600)

Commands (register with @BotFather):
    start   - Open the admin menu
    ban     - Ban a user from the group
    unban   - Unban a user
    mute    - Mute a user (restrict messages)
    unmute  - Unmute a user
    kick    - Remove a user from the group
    warn    - Warn a user (auto-bans at limit)
    unwarn  - Clear all warnings for a user
    stats   - Show group statistics
    users   - List active members
    pin     - Pin the replied-to message
    unpin   - Unpin a message
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from handlers import (
    admin_router,
    analytics_router,
    moderation_router,
    posting_router,
    welcome_router,
)
from middlewares.antispam import AntiSpamMiddleware

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Bot / Dispatcher setup ─────────────────────────────────────────────────

def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware — applied to all incoming messages
    dp.message.middleware(AntiSpamMiddleware())

    # Routers — order matters: specific before catch-all
    dp.include_router(welcome_router)
    dp.include_router(moderation_router)
    dp.include_router(analytics_router)
    dp.include_router(posting_router)
    dp.include_router(admin_router)  # catch-all tracker — must be last

    return dp


# ── Startup / shutdown hooks ───────────────────────────────────────────────

async def on_startup(bot: Bot) -> None:
    await db.init_db()
    me = await bot.get_me()
    logger.info("Bot started: @%s (id=%s)", me.username, me.id)


async def on_shutdown(bot: Bot) -> None:
    logger.info("Bot is shutting down — closing session.")
    await bot.session.close()


# ── Main ───────────────────────────────────────────────────────────────────

async def main() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling …")
    try:
        # allowed_updates includes chat_member so join/leave events are tracked
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "chat_member",
                "my_chat_member",
            ],
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Async SQLite database layer.

Tables
------
users       – every user the bot has ever seen in a managed chat
warnings    – per-user warning records
admin_log   – audit trail of every admin action
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)


# ── Bootstrap ──────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they do not exist yet."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER NOT NULL,
                chat_id     INTEGER NOT NULL,
                username    TEXT,
                full_name   TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1,
                joined_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                chat_id     INTEGER NOT NULL,
                reason      TEXT,
                warned_by   INTEGER NOT NULL,
                warned_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS admin_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                admin_id    INTEGER NOT NULL,
                action      TEXT    NOT NULL,
                target_id   INTEGER,
                details     TEXT,
                performed_at TEXT   NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH)


# ── Users ──────────────────────────────────────────────────────────────────

async def upsert_user(
    user_id: int,
    chat_id: int,
    username: Optional[str],
    full_name: str,
    is_active: bool = True,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, chat_id, username, full_name, is_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                is_active = excluded.is_active
            """,
            (user_id, chat_id, username, full_name, int(is_active)),
        )
        await db.commit()


async def set_user_active(user_id: int, chat_id: int, active: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_active = ? WHERE user_id = ? AND chat_id = ?",
            (int(active), user_id, chat_id),
        )
        await db.commit()


async def get_active_users(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE chat_id = ? AND is_active = 1 ORDER BY joined_at DESC",
            (chat_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_user_count(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE chat_id = ? AND is_active = 1",
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def get_total_user_count(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE chat_id = ?",
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


# ── Warnings ───────────────────────────────────────────────────────────────

async def add_warning(
    user_id: int,
    chat_id: int,
    reason: Optional[str],
    warned_by: int,
) -> int:
    """Insert a warning and return the new total count for this user in this chat."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (user_id, chat_id, reason, warned_by) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, reason, warned_by),
        )
        await db.commit()
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 1


async def get_warning_count(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def clear_warnings(user_id: int, chat_id: int) -> int:
    """Delete all warnings for a user and return how many were removed."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ) as cursor:
            row = await cursor.fetchone()
        count = row[0] if row else 0
        await db.execute(
            "DELETE FROM warnings WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        await db.commit()
    return count


# ── Admin log ──────────────────────────────────────────────────────────────

async def log_action(
    chat_id: int,
    admin_id: int,
    action: str,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO admin_log (chat_id, admin_id, action, target_id, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, admin_id, action, target_id, details),
        )
        await db.commit()


async def get_recent_actions(chat_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM admin_log
            WHERE chat_id = ?
            ORDER BY performed_at DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_action_count(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM admin_log WHERE chat_id = ?",
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0

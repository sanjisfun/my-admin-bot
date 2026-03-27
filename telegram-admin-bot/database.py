"""
Database operations for the admin bot.
"""

from __future__ import annotations

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

DB_PATH = "admin_bot.db"


async def init_db() -> None:
    """Initialize database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            reputation_score INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            is_banned BOOLEAN DEFAULT 0,
            banned_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chat_id)
        )
    """)

    # User roles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            assigned_by INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    # Action logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_user_id INTEGER,
            reason TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Spam filter rules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spam_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            rule_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Scheduled posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            created_by INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP
        )
    """)

    # Channel analytics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            message_id INTEGER,
            views INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0.0,
            reach INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chat settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            auto_delete_spam BOOLEAN DEFAULT 1,
            log_actions BOOLEAN DEFAULT 1,
            welcome_enabled BOOLEAN DEFAULT 1,
            reputation_enabled BOOLEAN DEFAULT 1,
            spam_sensitivity REAL DEFAULT 0.7,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Message history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message_id INTEGER,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Warnings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


async def upsert_user(
    user_id: int,
    chat_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    is_active: bool = True,
) -> None:
    """Insert or update user in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (user_id, chat_id, username, full_name, is_active, last_seen)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            username = COALESCE(?, username),
            full_name = COALESCE(?, full_name),
            is_active = ?,
            last_seen = CURRENT_TIMESTAMP
    """, (user_id, chat_id, username, full_name, is_active, username, full_name, is_active))

    conn.commit()
    conn.close()


async def log_action(
    chat_id: int,
    admin_id: int,
    action: str,
    target_user_id: Optional[int] = None,
    reason: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """Log an admin action."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO action_logs (chat_id, admin_id, action, target_user_id, reason, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_id, admin_id, action, target_user_id, reason, details))

    conn.commit()
    conn.close()


async def get_user_warnings(user_id: int, chat_id: int) -> int:
    """Get number of warnings for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM warnings WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))

    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def add_warning(
    user_id: int,
    chat_id: int,
    admin_id: int,
    reason: Optional[str] = None,
) -> None:
    """Add a warning to a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO warnings (user_id, chat_id, admin_id, reason)
        VALUES (?, ?, ?, ?)
    """, (user_id, chat_id, admin_id, reason))

    cursor.execute("""
        UPDATE users SET warnings = warnings + 1 WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))

    conn.commit()
    conn.close()


async def clear_warnings(user_id: int, chat_id: int) -> None:
    """Clear all warnings for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM warnings WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))

    cursor.execute("""
        UPDATE users SET warnings = 0 WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))

    conn.commit()
    conn.close()


async def get_chat_stats(chat_id: int) -> Dict[str, Any]:
    """Get statistics for a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total members
    cursor.execute("SELECT COUNT(*) FROM users WHERE chat_id = ?", (chat_id,))
    total_members = cursor.fetchone()[0]

    # Active today
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE chat_id = ? AND last_seen > datetime('now', '-1 day')
    """, (chat_id,))
    active_today = cursor.fetchone()[0]

    # Total messages
    cursor.execute("SELECT COUNT(*) FROM message_history WHERE chat_id = ?", (chat_id,))
    total_messages = cursor.fetchone()[0]

    # Warnings issued
    cursor.execute("SELECT COUNT(*) FROM warnings WHERE chat_id = ?", (chat_id,))
    total_warnings = cursor.fetchone()[0]

    # Bans
    cursor.execute("SELECT COUNT(*) FROM users WHERE chat_id = ? AND is_banned = 1", (chat_id,))
    total_bans = cursor.fetchone()[0]

    conn.close()

    return {
        "total_members": total_members,
        "active_today": active_today,
        "total_messages": total_messages,
        "total_warnings": total_warnings,
        "total_bans": total_bans,
    }


async def get_active_users(chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get most active users in a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, full_name, COUNT(*) as message_count
        FROM message_history
        WHERE chat_id = ?
        GROUP BY user_id
        ORDER BY message_count DESC
        LIMIT ?
    """, (chat_id, limit))

    users = []
    for row in cursor.fetchall():
        users.append({
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "message_count": row[3],
        })

    conn.close()
    return users


async def add_reputation(user_id: int, chat_id: int, points: int, reason: str) -> None:
    """Add reputation points to a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users SET reputation_score = reputation_score + ? 
        WHERE user_id = ? AND chat_id = ?
    """, (points, user_id, chat_id))

    await log_action(
        chat_id=chat_id,
        admin_id=user_id,
        action="reputation_change",
        target_user_id=user_id,
        reason=reason,
        details=f"points={points}"
    )

    conn.commit()
    conn.close()


async def get_reputation(user_id: int, chat_id: int) -> int:
    """Get user reputation score."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT reputation_score FROM users WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))

    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def assign_role(user_id: int, chat_id: int, role: str, admin_id: int) -> None:
    """Assign a role to a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_roles (user_id, chat_id, role, assigned_by)
        VALUES (?, ?, ?, ?)
    """, (user_id, chat_id, role, admin_id))

    conn.commit()
    conn.close()


async def get_user_roles(user_id: int, chat_id: int) -> List[str]:
    """Get all roles for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role FROM user_roles WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))

    roles = [row[0] for row in cursor.fetchall()]
    conn.close()
    return roles


async def schedule_post(
    channel_id: int,
    text: str,
    scheduled_time: datetime,
    created_by: int,
) -> int:
    """Schedule a post for a channel."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO scheduled_posts (channel_id, text, scheduled_time, created_by)
        VALUES (?, ?, ?, ?)
    """, (channel_id, text, scheduled_time, created_by))

    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


async def get_scheduled_posts(channel_id: int) -> List[Dict[str, Any]]:
    """Get all scheduled posts for a channel."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, text, scheduled_time, status FROM scheduled_posts
        WHERE channel_id = ? AND status = 'pending'
        ORDER BY scheduled_time ASC
    """, (channel_id,))

    posts = []
    for row in cursor.fetchall():
        posts.append({
            "id": row[0],
            "text": row[1],
            "scheduled_time": row[2],
            "status": row[3],
        })

    conn.close()
    return posts


async def get_channel_stats(channel_id: int) -> Dict[str, Any]:
    """Get statistics for a channel."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*), SUM(views), AVG(engagement_rate), SUM(reach)
        FROM channel_analytics
        WHERE channel_id = ?
    """, (channel_id,))

    result = cursor.fetchone()
    conn.close()

    return {
        "total_posts": result[0] if result[0] else 0,
        "total_views": result[1] if result[1] else 0,
        "avg_engagement": result[2] if result[2] else 0.0,
        "total_reach": result[3] if result[3] else 0,
    }

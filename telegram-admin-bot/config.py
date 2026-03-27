"""
Configuration for Telegram Admin Bot.
"""

import os
from typing import Optional

# ── Core ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# ── Moderation ─────────────────────────────────────────────────────────────
WARN_LIMIT = int(os.getenv("WARN_LIMIT", "3"))
DEFAULT_MUTE_SECONDS = int(os.getenv("DEFAULT_MUTE_SECONDS", "3600"))
AUTO_BAN_ENABLED = os.getenv("AUTO_BAN_ENABLED", "true").lower() == "true"
SPAM_FILTER_ENABLED = os.getenv("SPAM_FILTER_ENABLED", "true").lower() == "true"

# ── Analytics ──────────────────────────────────────────────────────────────
ANALYTICS_RETENTION_DAYS = int(os.getenv("ANALYTICS_RETENTION_DAYS", "30"))
TRACK_MESSAGE_EDITS = os.getenv("TRACK_MESSAGE_EDITS", "true").lower() == "true"
TRACK_DELETIONS = os.getenv("TRACK_DELETIONS", "true").lower() == "true"

# ── Channels ───────────────────────────────────────────────────────────────
CHANNEL_POSTING_ENABLED = os.getenv("CHANNEL_POSTING_ENABLED", "true").lower() == "true"
MAX_SCHEDULED_POSTS = int(os.getenv("MAX_SCHEDULED_POSTS", "50"))
AUTO_POST_ENABLED = os.getenv("AUTO_POST_ENABLED", "true").lower() == "true"

# ── Mini-App ───────────────────────────────────────────────────────────────
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://your-domain.com/miniapp")
MINIAPP_ENABLED = os.getenv("MINIAPP_ENABLED", "true").lower() == "true"

# ── Database ───────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///admin_bot.db")

# ── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_ACTIONS = os.getenv("LOG_ACTIONS", "true").lower() == "true"

# ── Advanced Features ──────────────────────────────────────────────────────
REPUTATION_SYSTEM_ENABLED = os.getenv("REPUTATION_SYSTEM_ENABLED", "true").lower() == "true"
ROLE_SYSTEM_ENABLED = os.getenv("ROLE_SYSTEM_ENABLED", "true").lower() == "true"
WELCOME_MESSAGE_ENABLED = os.getenv("WELCOME_MESSAGE_ENABLED", "true").lower() == "true"

# ── Spam Filter Settings ───────────────────────────────────────────────────
SPAM_SENSITIVITY = float(os.getenv("SPAM_SENSITIVITY", "0.7"))  # 0-1
AUTO_DELETE_SPAM = os.getenv("AUTO_DELETE_SPAM", "true").lower() == "true"
SPAM_WARN_THRESHOLD = int(os.getenv("SPAM_WARN_THRESHOLD", "3"))

# ── Rate Limiting ──────────────────────────────────────────────────────────
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "5"))
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

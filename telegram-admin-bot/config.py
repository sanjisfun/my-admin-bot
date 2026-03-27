import os

# ── Bot token ──────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]

# ── Persistence ────────────────────────────────────────────────────────────
DB_PATH: str = os.path.join(os.path.dirname(__file__), "Data", "bot.db")

# ── Moderation defaults ────────────────────────────────────────────────────
# How many warnings before an automatic ban
WARN_LIMIT: int = int(os.getenv("WARN_LIMIT", "3"))

# Default mute duration in seconds (1 hour)
DEFAULT_MUTE_SECONDS: int = int(os.getenv("DEFAULT_MUTE_SECONDS", "3600"))

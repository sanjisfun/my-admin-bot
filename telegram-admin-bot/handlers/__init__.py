"""
Handler package — exposes all routers for registration in main.py.

Import order matters: more specific routers must be registered before the
catch-all `admin` router so that command handlers take priority.
"""

from .welcome import router as welcome_router
from .moderation import router as moderation_router
from .analytics import router as analytics_router
from .posting import router as posting_router
from .admin import router as admin_router  # catch-all — must be last

__all__ = [
    "welcome_router",
    "moderation_router",
    "analytics_router",
    "posting_router",
    "admin_router",
]

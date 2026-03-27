"""
Handler routers for the admin bot.
"""

from .admin import router as admin_router
from .advanced_moderation import router as advanced_moderation_router
from .analytics import router as analytics_router
from .channel_management import router as channel_management_router
from .miniapp import router as miniapp_router
from .moderation import router as moderation_router
from .posting import router as posting_router
from .welcome import router as welcome_router

__all__ = [
    "admin_router",
    "advanced_moderation_router",
    "analytics_router",
    "channel_management_router",
    "miniapp_router",
    "moderation_router",
    "posting_router",
    "welcome_router",
]

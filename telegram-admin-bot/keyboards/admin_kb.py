"""
Inline keyboard factories for the admin bot.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Root admin menu shown after /start."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔨 Moderation", callback_data="menu:moderation"),
        InlineKeyboardButton(text="📊 Analytics",  callback_data="menu:analytics"),
    )
    builder.row(
        InlineKeyboardButton(text="📌 Pinning",    callback_data="menu:pinning"),
        InlineKeyboardButton(text="ℹ️ Help",        callback_data="menu:help"),
    )
    return builder.as_markup()


def moderation_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Ban",    callback_data="mod:ban"),
        InlineKeyboardButton(text="✅ Unban",  callback_data="mod:unban"),
    )
    builder.row(
        InlineKeyboardButton(text="🔇 Mute",   callback_data="mod:mute"),
        InlineKeyboardButton(text="🔊 Unmute", callback_data="mod:unmute"),
    )
    builder.row(
        InlineKeyboardButton(text="👢 Kick",   callback_data="mod:kick"),
    )
    builder.row(
        InlineKeyboardButton(text="⚠️ Warn",   callback_data="mod:warn"),
        InlineKeyboardButton(text="🗑 Unwarn", callback_data="mod:unwarn"),
    )
    builder.row(
        InlineKeyboardButton(text="« Back",    callback_data="menu:main"),
    )
    return builder.as_markup()


def analytics_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Stats",       callback_data="ana:stats"),
        InlineKeyboardButton(text="👥 Active users", callback_data="ana:users"),
    )
    builder.row(
        InlineKeyboardButton(text="« Back", callback_data="menu:main"),
    )
    return builder.as_markup()


def pinning_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📌 Pin message",   callback_data="pin:pin"),
        InlineKeyboardButton(text="📍 Unpin message", callback_data="pin:unpin"),
    )
    builder.row(
        InlineKeyboardButton(text="« Back", callback_data="menu:main"),
    )
    return builder.as_markup()


def confirm_action_kb(action: str, target_id: int) -> InlineKeyboardMarkup:
    """Generic yes/no confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Confirm",
            callback_data=f"confirm:{action}:{target_id}",
        ),
        InlineKeyboardButton(text="❌ Cancel", callback_data="confirm:cancel"),
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Main menu", callback_data="menu:main"))
    return builder.as_markup()

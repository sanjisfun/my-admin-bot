"""
Enhanced inline keyboard factories with new features.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Root admin menu with mini-app button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 Web Panel", web_app=WebAppInfo(url="https://your-domain.com/miniapp")),
    )
    builder.row(
        InlineKeyboardButton(text="🔨 Moderation", callback_data="menu:moderation"),
        InlineKeyboardButton(text="📊 Analytics",  callback_data="menu:analytics"),
    )
    builder.row(
        InlineKeyboardButton(text="📌 Pinning",    callback_data="menu:pinning"),
        InlineKeyboardButton(text="📢 Channels",   callback_data="menu:channels"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Settings",   callback_data="menu:settings"),
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
        InlineKeyboardButton(text="🔥 Advanced", callback_data="mod:advanced"),
    )
    builder.row(
        InlineKeyboardButton(text="« Back",    callback_data="menu:main"),
    )
    return builder.as_markup()


def advanced_moderation_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛡️ Spam Filter", callback_data="adv:spam"),
        InlineKeyboardButton(text="⭐ Reputation",  callback_data="adv:reputation"),
    )
    builder.row(
        InlineKeyboardButton(text="👔 Roles",      callback_data="adv:roles"),
        InlineKeyboardButton(text="📋 Logs",       callback_data="adv:logs"),
    )
    builder.row(
        InlineKeyboardButton(text="« Back",        callback_data="menu:moderation"),
    )
    return builder.as_markup()


def analytics_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Stats",       callback_data="ana:stats"),
        InlineKeyboardButton(text="👥 Active users", callback_data="ana:users"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Trends",      callback_data="ana:trends"),
        InlineKeyboardButton(text="🔝 Top posters",  callback_data="ana:top"),
    )
    builder.row(
        InlineKeyboardButton(text="« Back", callback_data="menu:main"),
    )
    return builder.as_markup()


def channels_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Schedule",    callback_data="ch:schedule"),
        InlineKeyboardButton(text="📊 Analytics",   callback_data="ch:analytics"),
    )
    builder.row(
        InlineKeyboardButton(text="📝 Templates",   callback_data="ch:templates"),
        InlineKeyboardButton(text="📢 Broadcast",   callback_data="ch:broadcast"),
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


def settings_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔔 Notifications", callback_data="set:notifications"),
        InlineKeyboardButton(text="🛡️ Security",     callback_data="set:security"),
    )
    builder.row(
        InlineKeyboardButton(text="🎨 Appearance",    callback_data="set:appearance"),
        InlineKeyboardButton(text="📝 Logs",          callback_data="set:logs"),
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

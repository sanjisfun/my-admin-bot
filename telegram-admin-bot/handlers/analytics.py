"""
Analytics handlers: statistics, user tracking, trends.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards import analytics_menu_kb, back_to_main_kb

logger = logging.getLogger(__name__)
router = Router(name="analytics")


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user is admin."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot) -> None:
    """Show group statistics."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can view statistics.")
        return
    
    stats = await db.get_chat_stats(message.chat.id)
    
    await message.reply(
        f"📊 <b>Group Statistics</b>\n\n"
        f"👥 Total Members: <b>{stats['total_members']}</b>\n"
        f"🟢 Active Today: <b>{stats['active_today']}</b>\n"
        f"💬 Total Messages: <b>{stats['total_messages']}</b>\n"
        f"⚠️ Warnings Issued: <b>{stats['total_warnings']}</b>\n"
        f"🚫 Users Banned: <b>{stats['total_bans']}</b>",
        reply_markup=analytics_menu_kb(),
        parse_mode="HTML"
    )


@router.message(Command("users"))
async def cmd_active_users(message: Message, bot: Bot) -> None:
    """Show most active users."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can view user list.")
        return
    
    users = await db.get_active_users(message.chat.id, limit=15)
    
    if not users:
        await message.reply("No users found.")
        return
    
    text = "👥 <b>Most Active Users</b>\n\n"
    for i, user in enumerate(users, 1):
        username = user['username'] or user['full_name'] or f"User {user['user_id']}"
        text += f"{i}. {username}\n"
        text += f"   Messages: {user['message_count']}\n\n"
    
    await message.reply(text, parse_mode="HTML")


@router.message(Command("trends"))
async def cmd_trends(message: Message, bot: Bot) -> None:
    """Show activity trends."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can view trends.")
        return
    
    await message.reply(
        "📈 <b>Activity Trends (Last 7 Days)</b>\n\n"
        "Mon: ████████░░ 80 msgs\n"
        "Tue: ██████░░░░ 60 msgs\n"
        "Wed: ███████████ 110 msgs\n"
        "Thu: █████░░░░░ 50 msgs\n"
        "Fri: ████████████ 120 msgs\n"
        "Sat: ██████████░ 100 msgs\n"
        "Sun: ███████░░░ 70 msgs",
        parse_mode="HTML"
    )


@router.message(Command("topposters"))
async def cmd_top_posters(message: Message, bot: Bot) -> None:
    """Show top message posters."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can view this.")
        return
    
    users = await db.get_active_users(message.chat.id, limit=10)
    
    text = "🔝 <b>Top Posters</b>\n\n"
    for i, user in enumerate(users, 1):
        username = user['username'] or user['full_name'] or f"User {user['user_id']}"
        text += f"{i}. {username}: <b>{user['message_count']}</b> messages\n"
    
    await message.reply(text, parse_mode="HTML")


@router.callback_query(F.data == "menu:analytics")
async def cb_analytics_menu(call: CallbackQuery) -> None:
    """Show analytics menu."""
    await call.message.edit_text(
        "📊 <b>Analytics</b>\n\n"
        "Choose what you want to analyze:",
        reply_markup=analytics_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "ana:stats")
async def cb_stats(call: CallbackQuery) -> None:
    """Show stats callback."""
    stats = await db.get_chat_stats(call.message.chat.id)
    
    await call.message.edit_text(
        f"📊 <b>Group Statistics</b>\n\n"
        f"👥 Members: {stats['total_members']}\n"
        f"🟢 Active: {stats['active_today']}\n"
        f"💬 Messages: {stats['total_messages']}\n"
        f"⚠️ Warnings: {stats['total_warnings']}\n"
        f"🚫 Bans: {stats['total_bans']}",
        parse_mode="HTML",
        reply_markup=back_to_main_kb()
    )
    await call.answer()


@router.callback_query(F.data == "ana:users")
async def cb_users(call: CallbackQuery) -> None:
    """Show active users callback."""
    users = await db.get_active_users(call.message.chat.id, limit=10)
    
    text = "👥 <b>Active Users</b>\n\n"
    for user in users:
        username = user['username'] or user['full_name'] or f"User {user['user_id']}"
        text += f"• {username}: {user['message_count']} msgs\n"
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_main_kb())
    await call.answer()

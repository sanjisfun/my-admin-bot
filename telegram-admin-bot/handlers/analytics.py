"""
Analytics handlers: /stats and /users.
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards import analytics_menu_kb, back_to_main_kb

logger = logging.getLogger(__name__)
router = Router(name="analytics")

# Maximum number of users to list in /users to keep messages readable
MAX_USERS_LISTED = 30


# ── /stats ─────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot) -> None:
    chat_id = message.chat.id

    try:
        chat = await bot.get_chat(chat_id)
        tg_count = chat.member_count or 0
    except Exception:
        tg_count = 0

    active_count = await db.get_user_count(chat_id)
    total_count = await db.get_total_user_count(chat_id)
    action_count = await db.get_action_count(chat_id)

    chat_title = message.chat.title or "this group"

    await message.reply(
        f"📊 <b>Statistics for {chat_title}</b>\n\n"
        f"👥 Telegram member count: <b>{tg_count}</b>\n"
        f"✅ Active members (DB):   <b>{active_count}</b>\n"
        f"📋 Total seen (DB):       <b>{total_count}</b>\n"
        f"🔨 Admin actions logged:  <b>{action_count}</b>",
        parse_mode="HTML",
    )


# ── /users ─────────────────────────────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: Message) -> None:
    chat_id = message.chat.id
    users = await db.get_active_users(chat_id)

    if not users:
        await message.reply(
            "👥 No active users found in the database yet.\n"
            "Users are tracked automatically as they send messages or join the group."
        )
        return

    lines: list[str] = []
    for i, u in enumerate(users[:MAX_USERS_LISTED], start=1):
        name = u.get("full_name") or "Unknown"
        username = f" (@{u['username']})" if u.get("username") else ""
        uid = u["user_id"]
        lines.append(f"{i}. <b>{name}</b>{username} — <code>{uid}</code>")

    header = f"👥 <b>Active members</b> ({min(len(users), MAX_USERS_LISTED)} of {len(users)}):\n\n"
    footer = (
        f"\n\n<i>Showing first {MAX_USERS_LISTED}. Total: {len(users)}.</i>"
        if len(users) > MAX_USERS_LISTED
        else ""
    )

    await message.reply(header + "\n".join(lines) + footer, parse_mode="HTML")


# ── Inline menu callbacks ──────────────────────────────────────────────────

@router.callback_query(F.data == "menu:analytics")
async def cb_analytics_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(  # type: ignore[union-attr]
        "📊 <b>Analytics</b>\n\nChoose a report:",
        reply_markup=analytics_menu_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "ana:stats")
async def cb_stats(call: CallbackQuery, bot: Bot) -> None:
    if call.message is None:
        await call.answer()
        return

    chat_id = call.message.chat.id

    try:
        chat = await bot.get_chat(chat_id)
        tg_count = chat.member_count or 0
    except Exception:
        tg_count = 0

    active_count = await db.get_user_count(chat_id)
    total_count = await db.get_total_user_count(chat_id)
    action_count = await db.get_action_count(chat_id)
    chat_title = call.message.chat.title or "this group"

    await call.message.edit_text(
        f"📊 <b>Statistics for {chat_title}</b>\n\n"
        f"👥 Telegram member count: <b>{tg_count}</b>\n"
        f"✅ Active members (DB):   <b>{active_count}</b>\n"
        f"📋 Total seen (DB):       <b>{total_count}</b>\n"
        f"🔨 Admin actions logged:  <b>{action_count}</b>",
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "ana:users")
async def cb_users(call: CallbackQuery) -> None:
    if call.message is None:
        await call.answer()
        return

    chat_id = call.message.chat.id
    users = await db.get_active_users(chat_id)

    if not users:
        await call.message.edit_text(
            "👥 No active users found in the database yet.",
            reply_markup=back_to_main_kb(),
        )
        await call.answer()
        return

    lines: list[str] = []
    for i, u in enumerate(users[:MAX_USERS_LISTED], start=1):
        name = u.get("full_name") or "Unknown"
        username = f" (@{u['username']})" if u.get("username") else ""
        uid = u["user_id"]
        lines.append(f"{i}. <b>{name}</b>{username} — <code>{uid}</code>")

    header = f"👥 <b>Active members</b> ({min(len(users), MAX_USERS_LISTED)} of {len(users)}):\n\n"
    footer = (
        f"\n\n<i>Showing first {MAX_USERS_LISTED}. Total: {len(users)}.</i>"
        if len(users) > MAX_USERS_LISTED
        else ""
    )

    await call.message.edit_text(
        header + "\n".join(lines) + footer,
        reply_markup=back_to_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()

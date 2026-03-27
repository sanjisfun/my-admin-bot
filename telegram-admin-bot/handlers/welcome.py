"""
Welcome handler — /start command and new-member tracking.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

import database as db
from keyboards import main_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="welcome")


# ── /start ─────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    admin_name = message.from_user.full_name if message.from_user else "Admin"
    await message.answer(
        f"👋 Hello, <b>{admin_name}</b>!\n\n"
        "I am your <b>Group Admin Bot</b>. Use the menu below to manage your group, "
        "or issue commands directly in the group chat.\n\n"
        "<b>Quick-reference commands:</b>\n"
        "  /ban, /unban — ban or unban a user\n"
        "  /mute, /unmute — restrict or restore messaging\n"
        "  /kick — remove a user from the group\n"
        "  /warn, /unwarn — issue or clear warnings\n"
        "  /stats — group statistics\n"
        "  /users — list active members\n"
        "  /pin, /unpin — pin or unpin a message\n\n"
        "All commands accept a reply or a user-id/username as the first argument.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ── Inline menu navigation ─────────────────────────────────────────────────

@router.callback_query(F.data == "menu:main")
async def cb_main_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(  # type: ignore[union-attr]
        "🏠 <b>Main menu</b> — choose a category:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(call: CallbackQuery) -> None:
    from keyboards import back_to_main_kb

    text = (
        "ℹ️ <b>Help</b>\n\n"
        "All moderation commands work in group chats. "
        "Reply to a user's message <i>or</i> pass their user-id / @username as the first argument.\n\n"
        "<b>Moderation</b>\n"
        "  /ban [id|@user] [reason] — permanently ban\n"
        "  /unban [id|@user] — lift a ban\n"
        "  /mute [id|@user] [seconds] — restrict messaging\n"
        "  /unmute [id|@user] — restore messaging\n"
        "  /kick [id|@user] — remove (can rejoin)\n"
        "  /warn [id|@user] [reason] — issue a warning\n"
        "  /unwarn [id|@user] — clear all warnings\n\n"
        "<b>Analytics</b>\n"
        "  /stats — group statistics\n"
        "  /users — list active members\n\n"
        "<b>Pinning</b>\n"
        "  /pin — pin the replied-to message\n"
        "  /unpin — unpin the replied-to message\n"
    )
    await call.message.edit_text(text, reply_markup=back_to_main_kb(), parse_mode="HTML")  # type: ignore[union-attr]
    await call.answer()


# ── Track new members ──────────────────────────────────────────────────────

@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated) -> None:
    """Upsert users into the database when they join or leave."""
    user = event.new_chat_member.user
    is_member = event.new_chat_member.status in ("member", "administrator", "creator")
    try:
        await db.upsert_user(
            user_id=user.id,
            chat_id=event.chat.id,
            username=user.username,
            full_name=user.full_name,
            is_active=is_member,
        )
    except Exception:
        logger.exception("Failed to upsert user %s", user.id)

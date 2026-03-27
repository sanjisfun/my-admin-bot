"""
Moderation handlers: ban, unban, mute, unmute, kick, warn, unwarn.

Usage pattern (all commands)
-----------------------------
  • Reply to a message  →  target is the replied-to user
  • /cmd @username       →  target resolved via get_chat_member
  • /cmd <user_id>       →  target resolved via get_chat_member

Admin-only: every handler verifies the caller is a chat administrator.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    ChatPermissions,
    Message,
)

import database as db
from config import DEFAULT_MUTE_SECONDS, WARN_LIMIT
from keyboards import back_to_main_kb, moderation_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="moderation")


# ── Helpers ────────────────────────────────────────────────────────────────

async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Return True if *user_id* is an administrator or creator of *chat_id*."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def _resolve_target(
    message: Message, bot: Bot, args: list[str]
) -> Optional[tuple[int, str]]:
    """
    Return (user_id, display_name) for the moderation target, or None on failure.

    Resolution order:
      1. Replied-to message author
      2. First argument as @username or numeric user-id
    """
    # 1. Reply target
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name

    # 2. Argument
    if args:
        raw = args[0]
        try:
            uid = int(raw)
        except ValueError:
            uid_str = raw.lstrip("@")
            try:
                member = await bot.get_chat_member(message.chat.id, uid_str)
                u = member.user
                return u.id, u.full_name
            except Exception:
                await message.reply(f"❌ Could not find user <code>{raw}</code>.", parse_mode="HTML")
                return None
        else:
            try:
                member = await bot.get_chat_member(message.chat.id, uid)
                u = member.user
                return u.id, u.full_name
            except Exception:
                await message.reply(f"❌ Could not find user <code>{uid}</code>.", parse_mode="HTML")
                return None

    await message.reply(
        "❌ Please reply to a message or provide a user-id / @username.",
        parse_mode="HTML",
    )
    return None


def _parse_args(message: Message) -> list[str]:
    """Return command arguments as a list of strings."""
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return []
    return parts[1].split()


async def _guard(message: Message, bot: Bot) -> bool:
    """
    Ensure the command is used in a group and the caller is an admin.
    Returns True if the caller may proceed.
    """
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("⚠️ This command only works in group chats.")
        return False
    if message.from_user is None:
        return False
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 You must be a group administrator to use this command.")
        return False
    return True


# ── /ban ───────────────────────────────────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"

    # Prevent banning other admins
    if await _is_admin(bot, message.chat.id, target_id):
        await message.reply("⚠️ Cannot ban a group administrator.")
        return

    try:
        await bot.ban_chat_member(message.chat.id, target_id)
        await db.set_user_active(target_id, message.chat.id, False)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="ban",
            target_id=target_id,
            details=reason,
        )
        await message.reply(
            f"🚫 <b>{target_name}</b> has been <b>banned</b>.\n"
            f"📝 Reason: {reason}",
            parse_mode="HTML",
        )
        logger.info("ban: admin=%s target=%s chat=%s", message.from_user.id, target_id, message.chat.id)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to ban: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to ban members.")


# ── /unban ─────────────────────────────────────────────────────────────────

@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result

    try:
        await bot.unban_chat_member(message.chat.id, target_id, only_if_banned=True)
        await db.set_user_active(target_id, message.chat.id, True)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="unban",
            target_id=target_id,
        )
        await message.reply(
            f"✅ <b>{target_name}</b> has been <b>unbanned</b>.",
            parse_mode="HTML",
        )
        logger.info("unban: admin=%s target=%s chat=%s", message.from_user.id, target_id, message.chat.id)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to unban: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to unban members.")


# ── /mute ──────────────────────────────────────────────────────────────────

@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result

    if await _is_admin(bot, message.chat.id, target_id):
        await message.reply("⚠️ Cannot mute a group administrator.")
        return

    # Optional duration argument (seconds)
    duration = DEFAULT_MUTE_SECONDS
    remaining_args = args[1:] if args else []
    if remaining_args:
        try:
            duration = int(remaining_args[0])
        except ValueError:
            pass

    until = datetime.now(tz=timezone.utc) + timedelta(seconds=duration)
    no_permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
    )

    try:
        await bot.restrict_chat_member(
            message.chat.id,
            target_id,
            permissions=no_permissions,
            until_date=until,
        )
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="mute",
            target_id=target_id,
            details=f"{duration}s",
        )
        human_duration = _human_duration(duration)
        await message.reply(
            f"🔇 <b>{target_name}</b> has been <b>muted</b> for {human_duration}.",
            parse_mode="HTML",
        )
        logger.info("mute: admin=%s target=%s duration=%ss chat=%s", message.from_user.id, target_id, duration, message.chat.id)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to mute: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to restrict members.")


def _human_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


# ── /unmute ────────────────────────────────────────────────────────────────

@router.message(Command("unmute"))
async def cmd_unmute(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result

    full_permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
    )

    try:
        await bot.restrict_chat_member(
            message.chat.id,
            target_id,
            permissions=full_permissions,
        )
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="unmute",
            target_id=target_id,
        )
        await message.reply(
            f"🔊 <b>{target_name}</b> has been <b>unmuted</b>.",
            parse_mode="HTML",
        )
        logger.info("unmute: admin=%s target=%s chat=%s", message.from_user.id, target_id, message.chat.id)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to unmute: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to change member permissions.")


# ── /kick ──────────────────────────────────────────────────────────────────

@router.message(Command("kick"))
async def cmd_kick(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"

    if await _is_admin(bot, message.chat.id, target_id):
        await message.reply("⚠️ Cannot kick a group administrator.")
        return

    try:
        # Ban then immediately unban = kick (user can rejoin via invite link)
        await bot.ban_chat_member(message.chat.id, target_id)
        await bot.unban_chat_member(message.chat.id, target_id)
        await db.set_user_active(target_id, message.chat.id, False)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="kick",
            target_id=target_id,
            details=reason,
        )
        await message.reply(
            f"👢 <b>{target_name}</b> has been <b>kicked</b>.\n"
            f"📝 Reason: {reason}",
            parse_mode="HTML",
        )
        logger.info("kick: admin=%s target=%s chat=%s", message.from_user.id, target_id, message.chat.id)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to kick: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to kick members.")


# ── /warn ──────────────────────────────────────────────────────────────────

@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"

    if await _is_admin(bot, message.chat.id, target_id):
        await message.reply("⚠️ Cannot warn a group administrator.")
        return

    warn_count = await db.add_warning(
        user_id=target_id,
        chat_id=message.chat.id,
        reason=reason,
        warned_by=message.from_user.id,  # type: ignore[union-attr]
    )
    await db.log_action(
        chat_id=message.chat.id,
        admin_id=message.from_user.id,  # type: ignore[union-attr]
        action="warn",
        target_id=target_id,
        details=f"warn {warn_count}/{WARN_LIMIT}: {reason}",
    )

    if warn_count >= WARN_LIMIT:
        # Auto-ban on reaching the limit
        try:
            await bot.ban_chat_member(message.chat.id, target_id)
            await db.set_user_active(target_id, message.chat.id, False)
            await db.log_action(
                chat_id=message.chat.id,
                admin_id=message.from_user.id,  # type: ignore[union-attr]
                action="auto_ban",
                target_id=target_id,
                details=f"Reached warn limit ({WARN_LIMIT})",
            )
            await message.reply(
                f"⚠️ <b>{target_name}</b> has received warning "
                f"<b>{warn_count}/{WARN_LIMIT}</b> and has been <b>automatically banned</b>.\n"
                f"📝 Reason: {reason}",
                parse_mode="HTML",
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            await message.reply(
                f"⚠️ <b>{target_name}</b> reached the warn limit but auto-ban failed: {exc}",
                parse_mode="HTML",
            )
    else:
        await message.reply(
            f"⚠️ <b>{target_name}</b> has been warned "
            f"(<b>{warn_count}/{WARN_LIMIT}</b>).\n"
            f"📝 Reason: {reason}",
            parse_mode="HTML",
        )
    logger.info("warn: admin=%s target=%s count=%s chat=%s", message.from_user.id, target_id, warn_count, message.chat.id)  # type: ignore[union-attr]


# ── /unwarn ────────────────────────────────────────────────────────────────

@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    args = _parse_args(message)
    result = await _resolve_target(message, bot, args)
    if result is None:
        return
    target_id, target_name = result

    removed = await db.clear_warnings(target_id, message.chat.id)
    await db.log_action(
        chat_id=message.chat.id,
        admin_id=message.from_user.id,  # type: ignore[union-attr]
        action="unwarn",
        target_id=target_id,
        details=f"Cleared {removed} warning(s)",
    )
    await message.reply(
        f"🗑 Cleared <b>{removed}</b> warning(s) for <b>{target_name}</b>.",
        parse_mode="HTML",
    )
    logger.info("unwarn: admin=%s target=%s removed=%s chat=%s", message.from_user.id, target_id, removed, message.chat.id)  # type: ignore[union-attr]


# ── Inline menu callbacks ──────────────────────────────────────────────────

@router.callback_query(F.data == "menu:moderation")
async def cb_moderation_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(  # type: ignore[union-attr]
        "🔨 <b>Moderation</b>\n\n"
        "Use the buttons below as a reminder, or issue commands directly in the group.\n"
        "All commands also accept a reply or <code>@username</code> / user-id.",
        reply_markup=moderation_menu_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# Generic callback for moderation sub-buttons (shows usage hint)
_MOD_HINTS: dict[str, str] = {
    "mod:ban":    "Use <code>/ban @user [reason]</code> in the group chat.",
    "mod:unban":  "Use <code>/unban @user</code> in the group chat.",
    "mod:mute":   "Use <code>/mute @user [seconds]</code> in the group chat.",
    "mod:unmute": "Use <code>/unmute @user</code> in the group chat.",
    "mod:kick":   "Use <code>/kick @user [reason]</code> in the group chat.",
    "mod:warn":   "Use <code>/warn @user [reason]</code> in the group chat.",
    "mod:unwarn": "Use <code>/unwarn @user</code> in the group chat.",
}


@router.callback_query(F.data.startswith("mod:"))
async def cb_mod_hint(call: CallbackQuery) -> None:
    hint = _MOD_HINTS.get(call.data or "", "Unknown action.")
    await call.answer(hint, show_alert=True)

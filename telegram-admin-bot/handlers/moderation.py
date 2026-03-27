"""
Moderation handlers: ban, mute, kick, warn.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, Message

import database as db
from config import WARN_LIMIT, DEFAULT_MUTE_SECONDS
from keyboards import moderation_menu_kb, confirm_action_kb, back_to_main_kb

logger = logging.getLogger(__name__)
router = Router(name="moderation")


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user is admin."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def _guard(message: Message, bot: Bot) -> bool:
    """Guard against non-admin usage."""
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
    """Ban a user. Usage: /ban <user_id> [reason]"""
    if not await _guard(message, bot):
        return
    
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "No reason"
    else:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.reply("Usage: /ban <user_id> [reason]")
            return
        try:
            user_id = int(parts[1])
            reason = parts[2] if len(parts) > 2 else "No reason"
        except ValueError:
            await message.reply("Invalid user ID")
            return
    
    try:
        await bot.ban_chat_member(message.chat.id, user_id)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            action="ban",
            target_user_id=user_id,
            reason=reason,
        )
        await message.reply(f"🚫 User {user_id} has been banned.\nReason: {reason}")
        logger.info(f"User {user_id} banned by {message.from_user.id}")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to ban: {e.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to ban users.")


# ── /unban ─────────────────────────────────────────────────────────────────

@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot) -> None:
    """Unban a user. Usage: /unban <user_id>"""
    if not await _guard(message, bot):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Usage: /unban <user_id>")
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.reply("Invalid user ID")
        return
    
    try:
        await bot.unban_chat_member(message.chat.id, user_id)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            action="unban",
            target_user_id=user_id,
        )
        await message.reply(f"✅ User {user_id} has been unbanned.")
        logger.info(f"User {user_id} unbanned by {message.from_user.id}")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to unban: {e.message}")


# ── /mute ──────────────────────────────────────────────────────────────────

@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot) -> None:
    """Mute a user. Usage: /mute <user_id> [duration_seconds] [reason]"""
    if not await _guard(message, bot):
        return
    
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        parts = message.text.split()
        duration = int(parts[1]) if len(parts) > 1 else DEFAULT_MUTE_SECONDS
        reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
    else:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 2:
            await message.reply("Usage: /mute <user_id> [duration] [reason]")
            return
        try:
            user_id = int(parts[1])
            duration = int(parts[2]) if len(parts) > 2 else DEFAULT_MUTE_SECONDS
            reason = parts[3] if len(parts) > 3 else "No reason"
        except ValueError:
            await message.reply("Invalid format")
            return
    
    try:
        until_date = datetime.now() + timedelta(seconds=duration)
        await bot.restrict_chat_member(
            message.chat.id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            action="mute",
            target_user_id=user_id,
            reason=reason,
            details=f"duration={duration}s",
        )
        await message.reply(f"🔇 User {user_id} muted for {duration}s.\nReason: {reason}")
        logger.info(f"User {user_id} muted by {message.from_user.id}")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to mute: {e.message}")


# ── /unmute ────────────────────────────────────────────────────────────────

@router.message(Command("unmute"))
async def cmd_unmute(message: Message, bot: Bot) -> None:
    """Unmute a user. Usage: /unmute <user_id>"""
    if not await _guard(message, bot):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Usage: /unmute <user_id>")
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.reply("Invalid user ID")
        return
    
    try:
        await bot.restrict_chat_member(
            message.chat.id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
            ),
        )
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            action="unmute",
            target_user_id=user_id,
        )
        await message.reply(f"🔊 User {user_id} has been unmuted.")
        logger.info(f"User {user_id} unmuted by {message.from_user.id}")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to unmute: {e.message}")


# ── /kick ──────────────────────────────────────────────────────────────────

@router.message(Command("kick"))
async def cmd_kick(message: Message, bot: Bot) -> None:
    """Kick a user. Usage: /kick <user_id> [reason]"""
    if not await _guard(message, bot):
        return
    
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "No reason"
    else:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.reply("Usage: /kick <user_id> [reason]")
            return
        try:
            user_id = int(parts[1])
            reason = parts[2] if len(parts) > 2 else "No reason"
        except ValueError:
            await message.reply("Invalid user ID")
            return
    
    try:
        await bot.kick_chat_member(message.chat.id, user_id)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            action="kick",
            target_user_id=user_id,
            reason=reason,
        )
        await message.reply(f"👢 User {user_id} has been kicked.\nReason: {reason}")
        logger.info(f"User {user_id} kicked by {message.from_user.id}")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to kick: {e.message}")


# ── /warn ──────────────────────────────────────────────────────────────────

@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot) -> None:
    """Warn a user. Usage: /warn <user_id> [reason]"""
    if not await _guard(message, bot):
        return
    
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "No reason"
    else:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.reply("Usage: /warn <user_id> [reason]")
            return
        try:
            user_id = int(parts[1])
            reason = parts[2] if len(parts) > 2 else "No reason"
        except ValueError:
            await message.reply("Invalid user ID")
            return
    
    try:
        await db.add_warning(user_id, message.chat.id, message.from_user.id, reason)
        warnings = await db.get_user_warnings(user_id, message.chat.id)
        
        await message.reply(
            f"⚠️ User {user_id} warned ({warnings}/{WARN_LIMIT})\n"
            f"Reason: {reason}"
        )
        
        if warnings >= WARN_LIMIT:
            await bot.ban_chat_member(message.chat.id, user_id)
            await db.log_action(
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                action="auto_ban",
                target_user_id=user_id,
                reason=f"Reached warning limit ({WARN_LIMIT})",
            )
            await message.reply(f"🚫 User {user_id} auto-banned (warning limit reached)")
        
        logger.info(f"User {user_id} warned by {message.from_user.id}")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")


# ── /unwarn ────────────────────────────────────────────────────────────────

@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message, bot: Bot) -> None:
    """Clear warnings for a user. Usage: /unwarn <user_id>"""
    if not await _guard(message, bot):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Usage: /unwarn <user_id>")
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.reply("Invalid user ID")
        return
    
    try:
        await db.clear_warnings(user_id, message.chat.id)
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            action="unwarn",
            target_user_id=user_id,
        )
        await message.reply(f"🗑 Warnings cleared for user {user_id}")
        logger.info(f"Warnings cleared for user {user_id} by {message.from_user.id}")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")


# ── Inline menu callbacks ──────────────────────────────────────────────────

@router.callback_query(F.data == "menu:moderation")
async def cb_moderation_menu(call: CallbackQuery) -> None:
    """Show moderation menu."""
    await call.message.edit_text(
        "🔨 <b>Moderation</b>\n\n"
        "Choose an action:",
        reply_markup=moderation_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()

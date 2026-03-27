"""
Posting / pinning handlers: /pin and /unpin.
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards import back_to_main_kb, pinning_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="posting")


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def _guard(message: Message, bot: Bot) -> bool:
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("⚠️ This command only works in group chats.")
        return False
    if message.from_user is None:
        return False
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 You must be a group administrator to use this command.")
        return False
    return True


# ── /pin ───────────────────────────────────────────────────────────────────

@router.message(Command("pin"))
async def cmd_pin(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    if not message.reply_to_message:
        await message.reply("📌 Reply to the message you want to pin.")
        return

    target_msg = message.reply_to_message
    try:
        await bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=target_msg.message_id,
            disable_notification=False,
        )
        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="pin",
            details=f"message_id={target_msg.message_id}",
        )
        await message.reply("📌 Message pinned successfully.")
        logger.info("pin: admin=%s msg=%s chat=%s", message.from_user.id, target_msg.message_id, message.chat.id)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to pin: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to pin messages.")


# ── /unpin ─────────────────────────────────────────────────────────────────

@router.message(Command("unpin"))
async def cmd_unpin(message: Message, bot: Bot) -> None:
    if not await _guard(message, bot):
        return

    try:
        if message.reply_to_message:
            # Unpin a specific message
            await bot.unpin_chat_message(
                chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id,
            )
            detail = f"message_id={message.reply_to_message.message_id}"
        else:
            # Unpin the most recently pinned message
            await bot.unpin_chat_message(chat_id=message.chat.id)
            detail = "most recent"

        await db.log_action(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,  # type: ignore[union-attr]
            action="unpin",
            details=detail,
        )
        await message.reply("📍 Message unpinned successfully.")
        logger.info("unpin: admin=%s chat=%s detail=%s", message.from_user.id, message.chat.id, detail)  # type: ignore[union-attr]
    except TelegramBadRequest as exc:
        await message.reply(f"❌ Failed to unpin: {exc.message}")
    except TelegramForbiddenError:
        await message.reply("❌ I don't have permission to unpin messages.")


# ── Inline menu callbacks ──────────────────────────────────────────────────

@router.callback_query(F.data == "menu:pinning")
async def cb_pinning_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(  # type: ignore[union-attr]
        "📌 <b>Pinning</b>\n\n"
        "Reply to a message in the group and use <code>/pin</code> or <code>/unpin</code>.\n"
        "Without a reply, <code>/unpin</code> removes the most recently pinned message.",
        reply_markup=pinning_menu_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("pin:"))
async def cb_pin_hint(call: CallbackQuery) -> None:
    hints = {
        "pin:pin":   "Reply to a message in the group and use /pin to pin it.",
        "pin:unpin": "Reply to a message in the group and use /unpin to unpin it.",
    }
    hint = hints.get(call.data or "", "Unknown action.")
    await call.answer(hint, show_alert=True)

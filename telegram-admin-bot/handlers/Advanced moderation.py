"""
Advanced moderation: spam filtering, reputation system, role management.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import database as db
from config import SPAM_SENSITIVITY, AUTO_DELETE_SPAM, SPAM_WARN_THRESHOLD
from keyboards import back_to_main_kb

logger = logging.getLogger(__name__)
router = Router(name="advanced_moderation")


class SpamFilter:
    """Configurable spam filter with pattern matching."""
    
    def __init__(self, sensitivity: float = 0.7):
        self.keywords = set()
        self.patterns = []
        self.sensitivity = sensitivity
        self._init_default_patterns()
    
    def _init_default_patterns(self) -> None:
        """Initialize default spam patterns."""
        # URLs
        self.patterns.append(re.compile(r'https?://\S+', re.IGNORECASE))
        # Repeated characters
        self.patterns.append(re.compile(r'(.)\1{4,}'))
        # Excessive mentions
        self.patterns.append(re.compile(r'@\w+\s+@\w+\s+@\w+'))
    
    def add_keyword(self, keyword: str) -> None:
        """Add keyword to filter."""
        self.keywords.add(keyword.lower())
    
    def add_pattern(self, pattern: str) -> None:
        """Add regex pattern to filter."""
        try:
            self.patterns.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
    
    def is_spam(self, text: str) -> Tuple[bool, str]:
        """Check if text is spam. Returns (is_spam, reason)."""
        if not text:
            return False, ""
        
        text_lower = text.lower()
        
        # Check keywords
        for keyword in self.keywords:
            if keyword in text_lower:
                return True, f"Contains blocked keyword: {keyword}"
        
        # Check patterns
        for pattern in self.patterns:
            if pattern.search(text):
                return True, "Matches spam pattern"
        
        # Check for excessive caps
        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.7:
                return True, "Excessive capitalization"
        
        # Check for excessive punctuation
        punct_count = sum(1 for c in text if c in '!?.')
        if len(text) > 5 and punct_count / len(text) > 0.3:
            return True, "Excessive punctuation"
        
        return False, ""


# Global spam filter instance
spam_filter = SpamFilter(SPAM_SENSITIVITY)


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user is admin."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


@router.message(F.text)
async def check_spam(message: Message, bot: Bot) -> None:
    """Check incoming messages for spam."""
    if message.from_user is None or message.chat.type not in ("group", "supergroup"):
        return
    
    if not message.text:
        return
    
    is_spam, reason = spam_filter.is_spam(message.text)
    
    if is_spam:
        try:
            if AUTO_DELETE_SPAM:
                await message.delete()
            
            # Log spam detection
            await db.log_action(
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                action="spam_detected",
                target_user_id=message.from_user.id,
                reason=reason,
            )
            
            # Add warning
            warnings = await db.get_user_warnings(message.from_user.id, message.chat.id)
            await db.add_warning(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                admin_id=bot.token.split(':')[0],
                reason=f"Spam: {reason}"
            )
            
            logger.info(f"Spam detected from {message.from_user.id}: {reason}")
        except Exception as e:
            logger.error(f"Failed to handle spam: {e}")


@router.message(Command("addspamkeyword"))
async def cmd_add_spam_keyword(message: Message, bot: Bot) -> None:
    """Add keyword to spam filter. Usage: /addspamkeyword <keyword>"""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can use this command.")
        return
    
    if not message.text:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Usage: /addspamkeyword <keyword>")
        return
    
    keyword = parts[1]
    spam_filter.add_keyword(keyword)
    
    await db.log_action(
        chat_id=message.chat.id,
        admin_id=message.from_user.id,
        action="spam_keyword_added",
        reason=keyword,
    )
    
    await message.reply(f"✅ Added '{keyword}' to spam filter")


@router.message(Command("reputation"))
async def cmd_reputation(message: Message) -> None:
    """Check user reputation. Usage: /reputation <user_id or reply>"""
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        username = message.reply_to_message.from_user.username or "Unknown"
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("Reply to a message or use: /reputation <user_id>")
            return
        try:
            user_id = int(parts[1])
            username = f"User {user_id}"
        except ValueError:
            await message.reply("Invalid user ID")
            return
    
    reputation = await db.get_reputation(user_id, message.chat.id)
    warnings = await db.get_user_warnings(user_id, message.chat.id)
    
    await message.reply(
        f"👤 <b>User Reputation</b>\n\n"
        f"User: {username}\n"
        f"ID: <code>{user_id}</code>\n"
        f"Score: <b>{reputation}</b>\n"
        f"Warnings: <b>{warnings}</b>",
        parse_mode="HTML"
    )


@router.message(Command("addrep"))
async def cmd_add_reputation(message: Message, bot: Bot) -> None:
    """Add reputation points. Usage: /addrep <user_id> <points> <reason>"""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can use this command.")
        return
    
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.reply("Usage: /addrep <user_id> <points> <reason>")
        return
    
    try:
        user_id = int(parts[1])
        points = int(parts[2])
        reason = parts[3]
    except ValueError:
        await message.reply("Invalid format. Usage: /addrep <user_id> <points> <reason>")
        return
    
    await db.add_reputation(user_id, message.chat.id, points, reason)
    
    emoji = "⬆️" if points > 0 else "⬇️"
    await message.reply(
        f"{emoji} <b>Reputation Updated</b>\n\n"
        f"User: <code>{user_id}</code>\n"
        f"Change: {points:+d}\n"
        f"Reason: {reason}",
        parse_mode="HTML"
    )


@router.message(Command("role"))
async def cmd_assign_role(message: Message, bot: Bot) -> None:
    """Assign role to user. Usage: /role <user_id> <role_name>"""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can use this command.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("Usage: /role <user_id> <role_name>")
        return
    
    try:
        user_id = int(parts[1])
        role = parts[2]
    except ValueError:
        await message.reply("Invalid user ID")
        return
    
    await db.assign_role(user_id, message.chat.id, role, message.from_user.id)
    
    await message.reply(
        f"👔 <b>Role Assigned</b>\n\n"
        f"User: <code>{user_id}</code>\n"
        f"Role: <b>{role}</b>",
        parse_mode="HTML"
    )


@router.message(Command("myroles"))
async def cmd_my_roles(message: Message) -> None:
    """Show your roles."""
    if message.from_user is None:
        return
    
    roles = await db.get_user_roles(message.from_user.id, message.chat.id)
    
    if not roles:
        await message.reply("You have no special roles.")
        return
    
    roles_text = "\n".join(f"• {role}" for role in roles)
    await message.reply(
        f"👔 <b>Your Roles</b>\n\n{roles_text}",
        parse_mode="HTML"
    )

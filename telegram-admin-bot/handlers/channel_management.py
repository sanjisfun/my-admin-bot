"""
Channel management: scheduled posts, analytics, templates, broadcasting.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import back_to_main_kb

logger = logging.getLogger(__name__)
router = Router(name="channel_management")


class ScheduleStates(StatesGroup):
    """FSM states for scheduling posts."""
    waiting_for_channel = State()
    waiting_for_text = State()
    waiting_for_time = State()


class PostTemplate:
    """Post template storage."""
    templates: Dict[int, Dict[str, str]] = {}
    
    @classmethod
    def save(cls, user_id: int, name: str, text: str) -> None:
        """Save a template."""
        if user_id not in cls.templates:
            cls.templates[user_id] = {}
        cls.templates[user_id][name] = text
    
    @classmethod
    def get(cls, user_id: int, name: str) -> Optional[str]:
        """Get a template."""
        return cls.templates.get(user_id, {}).get(name)
    
    @classmethod
    def list(cls, user_id: int) -> list[str]:
        """List all templates for user."""
        return list(cls.templates.get(user_id, {}).keys())
    
    @classmethod
    def delete(cls, user_id: int, name: str) -> bool:
        """Delete a template."""
        if user_id in cls.templates and name in cls.templates[user_id]:
            del cls.templates[user_id][name]
            return True
        return False


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user is admin."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


@router.message(Command("schedule"))
async def cmd_schedule_post(message: Message, state: FSMContext, bot: Bot) -> None:
    """Start scheduling a post."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can schedule posts.")
        return
    
    await state.set_state(ScheduleStates.waiting_for_channel)
    await message.reply(
        "📅 <b>Schedule Post</b>\n\n"
        "Enter the channel ID or username (e.g., @mychannel or -1001234567890):",
        parse_mode="HTML"
    )


@router.message(ScheduleStates.waiting_for_channel)
async def process_channel(message: Message, state: FSMContext) -> None:
    """Process channel input."""
    if not message.text:
        return
    
    await state.update_data(channel=message.text)
    await state.set_state(ScheduleStates.waiting_for_text)
    await message.reply(
        "📝 Now enter the post text:",
        parse_mode="HTML"
    )


@router.message(ScheduleStates.waiting_for_text)
async def process_post_text(message: Message, state: FSMContext) -> None:
    """Process post text."""
    if not message.text:
        return
    
    await state.update_data(text=message.text)
    await state.set_state(ScheduleStates.waiting_for_time)
    
    await message.reply(
        "⏰ Enter the scheduled time (format: YYYY-MM-DD HH:MM):\n\n"
        "Example: 2024-12-25 14:30",
        parse_mode="HTML"
    )


@router.message(ScheduleStates.waiting_for_time)
async def process_schedule_time(message: Message, state: FSMContext, bot: Bot) -> None:
    """Process and save scheduled post."""
    if not message.text:
        return
    
    try:
        scheduled_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.reply("❌ Invalid time format. Use: YYYY-MM-DD HH:MM")
        return
    
    data = await state.get_data()
    
    try:
        post_id = await db.schedule_post(
            channel_id=int(data["channel"]),
            text=data["text"],
            scheduled_time=scheduled_time,
            created_by=message.from_user.id,
        )
        
        await message.reply(
            f"✅ <b>Post Scheduled</b>\n\n"
            f"Post ID: <code>{post_id}</code>\n"
            f"Time: {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Status: Pending",
            parse_mode="HTML"
        )
        
        logger.info(f"Post scheduled: {post_id} for {scheduled_time}")
    except Exception as e:
        await message.reply(f"❌ Error scheduling post: {str(e)}")
    
    await state.clear()


@router.message(Command("channelstats"))
async def cmd_channel_stats(message: Message, bot: Bot) -> None:
    """Get channel statistics. Usage: /channelstats <channel_id>"""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can view channel stats.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Usage: /channelstats <channel_id>")
        return
    
    try:
        channel_id = int(parts[1])
    except ValueError:
        await message.reply("Invalid channel ID")
        return
    
    stats = await db.get_channel_stats(channel_id)
    
    await message.reply(
        f"📊 <b>Channel Statistics</b>\n\n"
        f"Total Posts: <b>{stats['total_posts']}</b>\n"
        f"Total Views: <b>{stats['total_views']:,}</b>\n"
        f"Avg Engagement: <b>{stats['avg_engagement']:.1%}</b>\n"
        f"Total Reach: <b>{stats['total_reach']:,}</b>",
        parse_mode="HTML"
    )


@router.message(Command("template"))
async def cmd_template(message: Message) -> None:
    """Manage post templates."""
    if not message.from_user:
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Create", callback_data="template:create"),
        InlineKeyboardButton(text="📋 List", callback_data="template:list"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Edit", callback_data="template:edit"),
        InlineKeyboardButton(text="🗑 Delete", callback_data="template:delete"),
    )
    
    await message.reply(
        "📝 <b>Post Templates</b>\n\n"
        "Manage your post templates for quick posting.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "template:list")
async def cb_list_templates(call: CallbackQuery) -> None:
    """List all templates."""
    if not call.from_user:
        return
    
    templates = PostTemplate.list(call.from_user.id)
    
    if not templates:
        text = "📋 <b>Your Templates</b>\n\nNo templates yet. Create one!"
    else:
        text = "📋 <b>Your Templates</b>\n\n" + "\n".join(f"• {t}" for t in templates)
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_main_kb())
    await call.answer()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot) -> None:
    """Broadcast message to multiple channels."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can broadcast.")
        return
    
    if not message.reply_to_message:
        await message.reply("Reply to a message to broadcast it.")
        return
    
    await message.reply(
        "📢 <b>Broadcast</b>\n\n"
        "Enter channel IDs separated by commas (e.g., @ch1, @ch2, -1001234567890):",
        parse_mode="HTML"
    )


@router.message(Command("scheduledposts"))
async def cmd_scheduled_posts(message: Message, bot: Bot) -> None:
    """List scheduled posts for a channel."""
    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("🚫 Only admins can view scheduled posts.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Usage: /scheduledposts <channel_id>")
        return
    
    try:
        channel_id = int(parts[1])
    except ValueError:
        await message.reply("Invalid channel ID")
        return
    
    posts = await db.get_scheduled_posts(channel_id)
    
    if not posts:
        await message.reply("No scheduled posts for this channel.")
        return
    
    text = "📅 <b>Scheduled Posts</b>\n\n"
    for post in posts:
        text += f"ID: {post['id']}\n"
        text += f"Time: {post['scheduled_time']}\n"
        text += f"Status: {post['status']}\n"
        text += f"Text: {post['text'][:50]}...\n\n"
    
    await message.reply(text, parse_mode="HTML")

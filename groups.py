"""
groups.py - Group & Invite Management
========================================
Functions for managing the promotion groups list and
sending invite messages to target groups.
"""

import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import database as db
import templates
import config

logger = logging.getLogger(__name__)


# ─── INVITE KEYBOARD ─────────────────────────────────────────────────────────

def build_invite_keyboard() -> InlineKeyboardMarkup:
    """Join button pointing to the MovYra main community."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🎬 Join MovYra Community", url=config.MAIN_GROUP_LINK
        )
    ]])


# ─── SEND SINGLE INVITE ──────────────────────────────────────────────────────

async def send_invite_to_group(
    bot: Bot, group_id: str, template_index: int = 0
) -> bool:
    """
    Send an invite message to `group_id` using the specified template.
    Returns True on success.
    """
    text     = templates.get_invite_template(template_index)
    keyboard = build_invite_keyboard()

    try:
        await bot.send_message(
            chat_id=group_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
        logger.info("Invite (template %d) sent to group %s", template_index, group_id)
        return True
    except TelegramError as e:
        logger.error("Failed to send invite to %s: %s", group_id, e)
        return False


# ─── WELCOME NEW MEMBER ──────────────────────────────────────────────────────

async def welcome_new_member(bot: Bot, chat_id: str, user_first_name: str) -> None:
    """Called when a new member joins the main MovYra community group."""
    text = (
        f"👋 Welcome, <b>{user_first_name}</b>, to <b>MovYra</b>! 🎬\n\n"
        "We're your #1 destination for movie reviews, OTT updates & more.\n\n"
        "📌 <b>Quick Rules:</b>\n"
        "  • Be respectful\n"
        "  • No spam or self-promo\n"
        "  • Stay on-topic (movies!)\n\n"
        f"🌐 <a href='{config.WEBSITE_BASE_URL}'>Visit movyra.com</a>"
    )
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML",
                               disable_web_page_preview=True)
    except TelegramError as e:
        logger.error("Welcome message failed: %s", e)


# ─── AUTO-DETECT GROUP (when bot is added) ────────────────────────────────────

async def handle_bot_added_to_group(bot: Bot, chat) -> None:
    """
    Called automatically when bot is added to a new group.
    Adds the group to DB if not already there.
    """
    group_id   = str(chat.id)
    group_name = chat.title or "Unknown Group"
    group_link = f"https://t.me/{chat.username}" if chat.username else ""

    if not db.group_exists(group_id):
        db.add_group(
            group_id=group_id,
            group_name=group_name,
            group_link=group_link,
            added_by="auto-detect",
        )
        logger.info("Auto-added new group: %s (%s)", group_name, group_id)

        # Greet the group
        try:
            await bot.send_message(
                group_id,
                (
                    f"👋 Hi everyone! I'm the <b>MovYra Bot</b>! 🎬\n\n"
                    "I'll be sharing the latest movie recommendations, "
                    "reviews, and OTT updates here.\n\n"
                    f"🌐 <a href='{config.WEBSITE_BASE_URL}'>movyra.com</a>"
                ),
                parse_mode="HTML",
            )
        except TelegramError:
            pass

"""
bot.py - MovYra Telegram Bot — Main Entry Point
================================================
Registers all command handlers and starts the bot.

Run with:   python bot.py
"""

import asyncio
import logging
import sys
from functools import wraps

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError

import config
import database as db
import promotions as promo_module
import groups as group_module
import scheduler
import templates

# ─── LOGGING SETUP ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─── ADMIN GUARD DECORATOR ────────────────────────────────────────────────────

def admin_only(func):
    """Decorator: only allow messages from ADMIN_IDS."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text(templates.NOT_ADMIN_MSG, parse_mode="HTML")
            return
        return await func(update, ctx)
    return wrapper


# ─── CONVERSATION STATES (for multi-step /addpromo) ──────────────────────────
(
    STATE_TITLE,
    STATE_DESC,
    STATE_RATING,
    STATE_GENRES,
    STATE_WEBSITE,
    STATE_TRAILER,
    STATE_IMAGE,
) = range(7)


# ═════════════════════════════════════════════════════════════════════════════
#  BASIC COMMANDS
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/start — welcome message."""
    user_id = update.effective_user.id
    if user_id in config.ADMIN_IDS:
        await update.message.reply_text(templates.WELCOME_ADMIN, parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"👋 Hi! I'm the <b>MovYra Bot</b> 🎬\n\n"
            f"Visit us at <a href='{config.WEBSITE_BASE_URL}'>movyra.com</a> "
            f"for the latest movie reviews & updates!\n\n"
            f"📢 <a href='{config.MAIN_GROUP_LINK}'>Join our community</a>",
            parse_mode="HTML",
        )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/help — show all commands."""
    await update.message.reply_text(templates.WELCOME_ADMIN, parse_mode="HTML")


# ═════════════════════════════════════════════════════════════════════════════
#  ADD PROMOTION (multi-step conversation)
# ═════════════════════════════════════════════════════════════════════════════

@admin_only
async def cmd_addpromo_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/addpromo — begin the add-promotion wizard."""
    await update.message.reply_text(
        "🎬 <b>Add New Promotion</b>\n\nStep 1/7: Enter the <b>movie title</b>:",
        parse_mode="HTML",
    )
    return STATE_TITLE


async def addpromo_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["promo_title"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 2/7: Enter a short <b>description</b> (2-3 lines):", parse_mode="HTML"
    )
    return STATE_DESC


async def addpromo_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["promo_desc"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 3/7: Enter the <b>rating</b> (e.g. 8.5):", parse_mode="HTML"
    )
    return STATE_RATING


async def addpromo_rating(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["promo_rating"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 4/7: Enter <b>genre tags</b> (e.g. #Action #Thriller):", parse_mode="HTML"
    )
    return STATE_GENRES


async def addpromo_genres(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["promo_genres"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 5/7: Enter the <b>MovYra website link</b> (e.g. https://movyra.com/movie-name):",
        parse_mode="HTML",
    )
    return STATE_WEBSITE


async def addpromo_website(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["promo_website"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 6/7: Enter the <b>YouTube trailer URL</b> (or send /skip):", parse_mode="HTML"
    )
    return STATE_TRAILER


async def addpromo_trailer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    ctx.user_data["promo_trailer"] = "" if text.lower() == "/skip" else text
    await update.message.reply_text(
        "Step 7/7: Send the <b>movie poster image URL</b> (or /skip):", parse_mode="HTML"
    )
    return STATE_IMAGE


async def addpromo_image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    ctx.user_data["promo_image"] = "" if text.lower() == "/skip" else text

    # Save to database
    promo_id = db.add_promotion(
        title        = ctx.user_data["promo_title"],
        description  = ctx.user_data["promo_desc"],
        website_link = ctx.user_data["promo_website"],
        image_url    = ctx.user_data.get("promo_image", ""),
        rating       = ctx.user_data.get("promo_rating", "8.0"),
        trailer_link = ctx.user_data.get("promo_trailer", ""),
        genres       = ctx.user_data.get("promo_genres", ""),
    )
    ctx.user_data.clear()

    await update.message.reply_text(
        f"✅ Promotion #{promo_id} added successfully!\n\n"
        "Use /listpromos to see all promotions.",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def addpromo_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Promotion not saved.")
    return ConversationHandler.END


# ═════════════════════════════════════════════════════════════════════════════
#  PROMOTION MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin_only
async def cmd_listpromos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/listpromos — show all promotions."""
    promos = db.get_all_promotions()
    if not promos:
        await update.message.reply_text("📭 No promotions yet. Use /addpromo to add one.")
        return

    lines = []
    for p in promos:
        status = "✅" if p["active"] else "⏸️"
        last   = p["last_sent"] or "Never"
        lines.append(
            f"{status} <b>#{p['id']}</b> — {p['title']}\n"
            f"   ⭐ {p['rating']} | Last sent: {last}\n"
            f"   🔗 {p['website_link']}"
        )

    text = "📋 <b>All Promotions</b>\n\n" + "\n\n".join(lines)
    # Telegram message limit is 4096 chars; split if needed
    if len(text) > 4000:
        text = text[:4000] + "\n\n… (truncated)"
    await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


@admin_only
async def cmd_deletepromo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/deletepromo [id] — delete a promotion."""
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /deletepromo [id]")
        return
    promo_id = int(args[0])
    if db.delete_promotion(promo_id):
        await update.message.reply_text(f"🗑️ Promotion #{promo_id} deleted.")
    else:
        await update.message.reply_text(f"❌ Promotion #{promo_id} not found.")


@admin_only
async def cmd_editpromo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/editpromo [id] [field] [value] — inline quick edit."""
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /editpromo [id] [field] [new value]\n\n"
            "Fields: title | description | rating | genres | website_link | trailer_link | image_url | active\n\n"
            "Example:\n/editpromo 3 rating 9.1"
        )
        return

    promo_id = int(args[0]) if args[0].isdigit() else None
    if promo_id is None:
        await update.message.reply_text("❌ Invalid promotion ID.")
        return

    field = args[1].lower()
    value = " ".join(args[2:])

    # Validate 'active' field
    if field == "active":
        value = "1" if value.lower() in ("1", "true", "yes", "on") else "0"

    if db.update_promotion(promo_id, **{field: value}):
        await update.message.reply_text(
            f"✅ Promotion #{promo_id}: <b>{field}</b> updated to:\n{value}",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(f"❌ Could not update promotion #{promo_id}.")


# ═════════════════════════════════════════════════════════════════════════════
#  SCHEDULER CONTROL
# ═════════════════════════════════════════════════════════════════════════════

@admin_only
async def cmd_pause(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/pause — pause auto-posting."""
    db.set_setting("paused", "1")
    await update.message.reply_text(templates.PAUSED_MSG, parse_mode="HTML")


@admin_only
async def cmd_resume(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/resume — resume auto-posting."""
    db.set_setting("paused", "0")
    await update.message.reply_text(templates.RESUMED_MSG, parse_mode="HTML")


@admin_only
async def cmd_setinterval(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/setinterval [minutes] — change posting frequency."""
    args = ctx.args
    if not args or not args[0].isdigit():
        current = db.get_setting("interval_minutes") or str(config.DEFAULT_INTERVAL_MINUTES)
        await update.message.reply_text(
            f"Current interval: <b>{current} minutes</b>\n\nUsage: /setinterval [minutes]",
            parse_mode="HTML",
        )
        return

    minutes = int(args[0])
    if minutes < 1:
        await update.message.reply_text("❌ Minimum interval is 1 minute.")
        return

    db.set_setting("interval_minutes", str(minutes))
    await update.message.reply_text(
        f"⏱️ Posting interval set to <b>{minutes} minutes</b>.", parse_mode="HTML"
    )


@admin_only
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/status — show bot health summary."""
    stats    = db.get_send_stats()
    paused   = db.get_setting("paused") == "1"
    interval = db.get_setting("interval_minutes") or str(config.DEFAULT_INTERVAL_MINUTES)

    state = "⏸️ PAUSED" if paused else "▶️ RUNNING"

    text = (
        f"📊 <b>MovYra Bot Status</b>\n\n"
        f"State:          {state}\n"
        f"Interval:       {interval} min\n"
        f"Active promos:  {stats['active_promos']}\n"
        f"Active groups:  {stats['active_groups']}\n"
        f"Total sent:     {stats['total_sent']}\n"
        f"Total failed:   {stats['total_failed']}\n"
        f"Version:        {config.BOT_VERSION}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/broadcast — immediately send next promo to all groups."""
    promo = promo_module.get_next_promo()
    if not promo:
        await update.message.reply_text("📭 No active promotions to broadcast.")
        return

    await update.message.reply_text(
        f"📣 Broadcasting <b>{promo['title']}</b> to all groups…", parse_mode="HTML"
    )
    admin_id = update.effective_user.id
    summary  = await promo_module.broadcast_promotion(
        update.get_bot(), promo, notify_admin_id=admin_id
    )
    # broadcast_promotion already sends the summary message to admin


# ═════════════════════════════════════════════════════════════════════════════
#  GROUP MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin_only
async def cmd_addgroup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/addgroup [group_id] [group_name] — add a group to the list."""
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /addgroup [group_id] [group name]\n\n"
            "Example: /addgroup -1001234567890 MyMovieGroup"
        )
        return

    group_id   = args[0]
    group_name = " ".join(args[1:])
    added_by   = update.effective_user.username or str(update.effective_user.id)

    if db.add_group(group_id, group_name, added_by=added_by):
        await update.message.reply_text(
            f"✅ Group added:\n<b>{group_name}</b> ({group_id})", parse_mode="HTML"
        )
    else:
        await update.message.reply_text(f"ℹ️ Group {group_id} already exists.")


@admin_only
async def cmd_removegroup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/removegroup [group_id] — remove (deactivate) a group."""
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /removegroup [group_id]")
        return

    if db.remove_group(args[0]):
        await update.message.reply_text(f"🗑️ Group {args[0]} removed.")
    else:
        await update.message.reply_text(f"❌ Group {args[0]} not found.")


@admin_only
async def cmd_listgroups(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/listgroups — list all connected groups."""
    groups = db.get_all_groups()
    if not groups:
        await update.message.reply_text("📭 No groups registered yet.")
        return

    lines = []
    for g in groups:
        status = "✅" if g["active"] else "⏸️"
        link   = g["group_link"] or "no link"
        lines.append(f"{status} <b>{g['group_name']}</b>\n   ID: {g['group_id']} | {link}")

    text = "👥 <b>Registered Groups</b>\n\n" + "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n… (truncated)"
    await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


# ═════════════════════════════════════════════════════════════════════════════
#  INVITE MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin_only
async def cmd_setinvite(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/setinvite [1-5] — set the default invite template number."""
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: /setinvite [1-5]\n\nTemplates:\n"
            "1 = Movie Lover\n2 = Review/Discussion\n"
            "3 = OTT Updates\n4 = Regional Cinema\n5 = General Entertainment"
        )
        return

    idx = int(args[0]) - 1   # 0-based internally
    db.set_setting("invite_template", str(idx))
    await update.message.reply_text(
        f"✅ Default invite template set to #{args[0]}.\n\n"
        f"Preview:\n\n{templates.get_invite_template(idx)}"
    )


@admin_only
async def cmd_sendinvite(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/sendinvite [group_id] — send invite to a specific group."""
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /sendinvite [group_id]")
        return

    group_id = args[0]
    idx      = int(db.get_setting("invite_template") or 0)
    ok       = await group_module.send_invite_to_group(update.get_bot(), group_id, idx)
    if ok:
        await update.message.reply_text(f"✅ Invite sent to {group_id}.")
    else:
        await update.message.reply_text(f"❌ Failed to send invite to {group_id}.")


# ═════════════════════════════════════════════════════════════════════════════
#  WEBSITE / API INTEGRATION COMMANDS  (/movie  /trending  /toprated)
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_movie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/movie [name] — fetch movie info from the MovYra API."""
    if not ctx.args:
        await update.message.reply_text("Usage: /movie [movie name]\nExample: /movie Inception")
        return

    movie_name = " ".join(ctx.args)
    await update.message.reply_text(f"🔍 Searching for <b>{movie_name}</b>…", parse_mode="HTML")

    try:
        import aiohttp
        url = f"{config.WEBSITE_API_URL}/movies/search?q={movie_name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Adjust keys based on your actual API response shape
                    movie = data.get("results", [{}])[0]
                    text  = (
                        f"🎬 <b>{movie.get('title', movie_name)}</b>\n\n"
                        f"⭐ Rating: {movie.get('rating', 'N/A')}/10\n"
                        f"📅 Year: {movie.get('year', 'N/A')}\n"
                        f"🏷️ {movie.get('genres', '')}\n\n"
                        f"📝 {movie.get('description', 'No description available.')}\n\n"
                        f"🔗 <a href='{config.WEBSITE_BASE_URL}/movie/{movie.get(\"slug\", \"\")}'>Read full review</a>"
                    )
                    await update.message.reply_text(text, parse_mode="HTML",
                                                    disable_web_page_preview=False)
                else:
                    await update.message.reply_text(f"❌ Movie '{movie_name}' not found on MovYra.")
    except Exception as e:
        logger.error("/movie command error: %s", e)
        await update.message.reply_text(
            f"⚠️ Could not reach MovYra API right now. "
            f"Try visiting <a href='{config.WEBSITE_BASE_URL}'>movyra.com</a> directly.",
            parse_mode="HTML",
        )


async def cmd_trending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/trending — get trending movies from the MovYra API."""
    await _fetch_and_send_movie_list(update, "trending", "📈 Trending on MovYra")


async def cmd_toprated(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/toprated — get top-rated movies from the MovYra API."""
    await _fetch_and_send_movie_list(update, "top-rated", "🏆 Top Rated on MovYra")


async def _fetch_and_send_movie_list(update, endpoint: str, heading: str):
    try:
        import aiohttp
        url = f"{config.WEBSITE_API_URL}/movies/{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data    = await resp.json()
                    movies  = data.get("results", [])[:10]
                    lines   = [
                        f"{i+1}. <b>{m['title']}</b> — ⭐ {m.get('rating','?')}/10"
                        for i, m in enumerate(movies)
                    ]
                    text = (
                        f"{heading}\n\n" +
                        "\n".join(lines) +
                        f"\n\n🌐 <a href='{config.WEBSITE_BASE_URL}/{endpoint}'>See all on MovYra</a>"
                    )
                    await update.message.reply_text(text, parse_mode="HTML",
                                                    disable_web_page_preview=True)
                else:
                    await update.message.reply_text("❌ Could not fetch data from MovYra.")
    except Exception as e:
        logger.error("Movie list fetch error: %s", e)
        await update.message.reply_text(
            f"⚠️ MovYra API unavailable. Visit <a href='{config.WEBSITE_BASE_URL}'>movyra.com</a>",
            parse_mode="HTML",
        )


# ═════════════════════════════════════════════════════════════════════════════
#  NEW MEMBER WELCOME  (group event handler)
# ═════════════════════════════════════════════════════════════════════════════

async def handle_new_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Welcome new members in any group the bot is in."""
    chat = update.effective_chat

    for member in update.message.new_chat_members:
        if member.is_bot:
            # Bot itself was added to a group — register the group
            await group_module.handle_bot_added_to_group(update.get_bot(), chat)
        else:
            # Real user joined — send welcome only in the main community
            if str(chat.id) == str(config.MAIN_GROUP_ID):
                await group_module.welcome_new_member(
                    update.get_bot(), str(chat.id), member.first_name
                )


# ═════════════════════════════════════════════════════════════════════════════
#  SPAM / MODERATION  (very basic example)
# ═════════════════════════════════════════════════════════════════════════════

# Words to auto-delete (extend as needed)
SPAM_KEYWORDS = ["t.me/+", "bit.ly", "join now free", "earn money", "click here now"]

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Basic spam filter for the main group."""
    if str(update.effective_chat.id) != str(config.MAIN_GROUP_ID):
        return

    text = (update.message.text or "").lower()
    if any(kw in text for kw in SPAM_KEYWORDS):
        try:
            await update.message.delete()
            await ctx.bot.send_message(
                update.effective_chat.id,
                f"⚠️ @{update.effective_user.username or 'User'}, "
                "spam links are not allowed.",
            )
        except TelegramError:
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  APPLICATION SETUP & MAIN
# ═════════════════════════════════════════════════════════════════════════════

def build_application() -> Application:
    """Wire up all handlers and return the Application object."""
    app = Application.builder().token(config.BOT_TOKEN).build()

    # ── /addpromo conversation ────────────────────────────────────────────────
    addpromo_conv = ConversationHandler(
        entry_points=[CommandHandler("addpromo", cmd_addpromo_start)],
        states={
            STATE_TITLE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, addpromo_title)],
            STATE_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, addpromo_desc)],
            STATE_RATING:  [MessageHandler(filters.TEXT & ~filters.COMMAND, addpromo_rating)],
            STATE_GENRES:  [MessageHandler(filters.TEXT & ~filters.COMMAND, addpromo_genres)],
            STATE_WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addpromo_website)],
            STATE_TRAILER: [MessageHandler(filters.TEXT, addpromo_trailer)],  # /skip allowed
            STATE_IMAGE:   [MessageHandler(filters.TEXT, addpromo_image)],
        },
        fallbacks=[CommandHandler("cancel", addpromo_cancel)],
        conversation_timeout=300,  # 5-minute timeout
    )

    # ── Register all handlers ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("help",          cmd_help))
    app.add_handler(addpromo_conv)
    app.add_handler(CommandHandler("listpromos",    cmd_listpromos))
    app.add_handler(CommandHandler("editpromo",     cmd_editpromo))
    app.add_handler(CommandHandler("deletepromo",   cmd_deletepromo))
    app.add_handler(CommandHandler("pause",         cmd_pause))
    app.add_handler(CommandHandler("resume",        cmd_resume))
    app.add_handler(CommandHandler("setinterval",   cmd_setinterval))
    app.add_handler(CommandHandler("status",        cmd_status))
    app.add_handler(CommandHandler("broadcast",     cmd_broadcast))
    app.add_handler(CommandHandler("addgroup",      cmd_addgroup))
    app.add_handler(CommandHandler("removegroup",   cmd_removegroup))
    app.add_handler(CommandHandler("listgroups",    cmd_listgroups))
    app.add_handler(CommandHandler("setinvite",     cmd_setinvite))
    app.add_handler(CommandHandler("sendinvite",    cmd_sendinvite))
    app.add_handler(CommandHandler("movie",         cmd_movie))
    app.add_handler(CommandHandler("trending",      cmd_trending))
    app.add_handler(CommandHandler("toprated",      cmd_toprated))

    # Group events
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member)
    )
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message)
    )

    return app


async def post_init(application: Application) -> None:
    """Called after the bot starts — kicks off background tasks."""
    bot = application.bot
    asyncio.create_task(scheduler.promo_loop(bot))
    asyncio.create_task(scheduler.daily_loop(bot))
    logger.info("Background tasks started.")


def main():
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set! Add it to your .env file.")
        sys.exit(1)
    if not config.ADMIN_IDS:
        logger.warning("No ADMIN_IDS set. You won't be able to use admin commands.")

    # Initialise DB
    db.init_db()
    db.backup_database()

    # Build & run
    app = build_application()
    app.post_init = post_init   # type: ignore

    logger.info("Starting MovYra Bot v%s …", config.BOT_VERSION)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

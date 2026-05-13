"""
scheduler.py - MovYra Auto-Posting Scheduler
=============================================
Two separate loops:
  1. promo_loop  — sends a rotating promotion every N minutes
  2. daily_loop  — posts daily content at scheduled times (9am, 2pm, 6pm, 8pm IST)

Both loops run as asyncio tasks inside the bot's application.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytz
from telegram import Bot
from telegram.error import TelegramError

import database as db
import promotions as promo_module
import config

logger = logging.getLogger(__name__)

# India Standard Time (UTC+5:30)
IST = pytz.timezone("Asia/Kolkata")


# ─── PROMO LOOP ───────────────────────────────────────────────────────────────

async def promo_loop(bot: Bot) -> None:
    """
    Infinite loop: every N minutes, pick the next promo and send it to all groups.
    Checks the 'paused' setting before each cycle.
    Interval is read fresh each cycle so admin changes take effect immediately.
    """
    logger.info("Promo loop started.")

    while True:
        try:
            paused   = db.get_setting("paused") == "1"
            interval = int(db.get_setting("interval_minutes") or config.DEFAULT_INTERVAL_MINUTES)

            if paused:
                logger.debug("Scheduler is paused. Sleeping 60s.")
                await asyncio.sleep(60)
                continue

            promo = promo_module.get_next_promo()
            if not promo:
                logger.warning("No active promotions. Sleeping %d min.", interval)
                await asyncio.sleep(interval * 60)
                continue

            logger.info("Auto-posting promo: %s", promo["title"])
            groups  = db.get_active_groups()
            sent = failed = skipped = 0

            for i, group in enumerate(groups):
                gid = group["group_id"]

                if db.was_recently_sent(promo["id"], gid):
                    skipped += 1
                    continue

                ok = await promo_module.send_promotion_to_group(bot, promo, gid)
                if ok:
                    sent += 1
                else:
                    failed += 1
                    # Schedule a retry for this group after RETRY_DELAY_MINUTES
                    asyncio.create_task(
                        _retry_send(bot, promo, gid, delay_min=config.RETRY_DELAY_MINUTES)
                    )

                await asyncio.sleep(config.SEND_DELAY_SECONDS)
                if (i + 1) % config.GROUP_BATCH_SIZE == 0:
                    await asyncio.sleep(config.BATCH_DELAY_SECONDS)

            logger.info(
                "Promo cycle done — sent=%d failed=%d skipped=%d. "
                "Next in %d min.", sent, failed, skipped, interval
            )

            # Notify admins about the cycle
            _notify_admins(bot, promo["title"], sent, failed, skipped)

        except Exception as e:
            logger.exception("Unexpected error in promo_loop: %s", e)

        # Sleep for the configured interval
        interval = int(db.get_setting("interval_minutes") or config.DEFAULT_INTERVAL_MINUTES)
        await asyncio.sleep(interval * 60)


async def _retry_send(bot: Bot, promo, group_id: str, delay_min: int = 5) -> None:
    """Wait `delay_min` minutes then try sending the promo to the group again."""
    await asyncio.sleep(delay_min * 60)
    logger.info("Retrying promo %d → group %s", promo["id"], group_id)
    await promo_module.send_promotion_to_group(bot, promo, group_id)


def _notify_admins(bot: Bot, promo_title: str, sent: int, failed: int, skipped: int) -> None:
    """Fire-and-forget coroutine to message all admins."""
    msg = (
        f"✅ <b>Auto-post complete</b>\n\n"
        f"🎬 <b>{promo_title}</b>\n"
        f"Sent: {sent} | Failed: {failed} | Skipped: {skipped}"
    )
    for admin_id in config.ADMIN_IDS:
        asyncio.create_task(_safe_send(bot, admin_id, msg))


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML")
    except TelegramError:
        pass


# ─── DAILY CONTENT LOOP ───────────────────────────────────────────────────────

async def daily_loop(bot: Bot) -> None:
    """
    Runs forever. At each scheduled time (IST), posts a different type of content
    to the main MovYra community group.

    The loop wakes up every minute to check if it's time to post.
    Tracks last-posted date per slot so it never double-posts.
    """
    if not config.MAIN_GROUP_ID:
        logger.warning("MAIN_GROUP_ID not set — daily loop disabled.")
        return

    logger.info("Daily content loop started for group %s", config.MAIN_GROUP_ID)

    # Track what was last posted (date string)
    last_posted: dict = {
        "morning": "", "afternoon": "", "evening": "", "night": ""
    }

    schedule = {
        "morning":   config.SCHEDULE_MORNING,
        "afternoon": config.SCHEDULE_AFTERNOON,
        "evening":   config.SCHEDULE_EVENING,
        "night":     config.SCHEDULE_NIGHT,
    }

    while True:
        try:
            now      = datetime.now(IST)
            today    = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M")

            for slot, slot_time in schedule.items():
                if time_str == slot_time and last_posted[slot] != today:
                    last_posted[slot] = today
                    asyncio.create_task(
                        _post_daily_content(bot, slot)
                    )

        except Exception as e:
            logger.exception("Error in daily_loop: %s", e)

        await asyncio.sleep(60)   # check every minute


async def _post_daily_content(bot: Bot, slot: str) -> None:
    """
    Post the right content type for the given time slot.
    In production, fetch real data from the MovYra API.
    Here we use placeholder content — replace with actual API calls.
    """
    gid = config.MAIN_GROUP_ID
    if not gid:
        return

    import templates

    try:
        if slot == "morning":
            # TODO: fetch today's pick from website API
            text = templates.daily_recommendation(
                movie_name="Today's Featured Movie",
                reason="Highly rated by MovYra critics — a must-watch this week!",
                link=f"{config.WEBSITE_BASE_URL}/featured",
            )

        elif slot == "afternoon":
            # TODO: fetch real trending list
            text = templates.trending_update([
                (1, "Movie A", "9.2"),
                (2, "Movie B", "8.8"),
                (3, "Movie C", "8.5"),
            ])

        elif slot == "evening":
            # TODO: fetch real OTT calendar
            text = templates.ott_release_alert([
                ("Netflix",   "New Release A", "Today"),
                ("Prime",     "New Release B", "Tomorrow"),
                ("Disney+",   "New Release C", "This Week"),
            ])

        elif slot == "night":
            # TODO: use Telegram polls for interactivity
            text = templates.movie_trivia(
                question="Which movie won the Best Picture Oscar in 2024?",
                options=["Oppenheimer", "Poor Things", "Anatomy of a Fall", "Past Lives"],
            )

        else:
            return

        await bot.send_message(gid, text, parse_mode="HTML",
                               disable_web_page_preview=True)
        logger.info("Daily %s content posted.", slot)

    except TelegramError as e:
        logger.error("Failed to post daily %s content: %s", slot, e)

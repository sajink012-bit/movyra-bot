"""
promotions.py - Promotion Management
=====================================
High-level helpers for sending a single promotion to a single group,
and for building the inline keyboard (buttons) attached to each promo.
"""

import asyncio
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import database as db
import templates
import config

logger = logging.getLogger(__name__)


# ─── KEYBOARD BUILDER ─────────────────────────────────────────────────────────

def build_promo_keyboard(promo) -> InlineKeyboardMarkup:
    """
    Build the inline button row for a promotion:
      [Watch Trailer]  [MovYra Website]
      [Join MovYra Community]
    """
    buttons = []

    row1 = []
    if promo["trailer_link"]:
        row1.append(InlineKeyboardButton("🎬 Watch Trailer", url=promo["trailer_link"]))
    row1.append(InlineKeyboardButton("🌐 MovYra Website", url=promo["website_link"]))

    row2 = [
        InlineKeyboardButton(
            "📢 Join MovYra Community", url=config.MAIN_GROUP_LINK
        )
    ]

    buttons.append(row1)
    buttons.append(row2)
    return InlineKeyboardMarkup(buttons)


# ─── SINGLE-SEND FUNCTION ─────────────────────────────────────────────────────

async def send_promotion_to_group(
    bot: Bot, promo, group_id: str
) -> bool:
    """
    Send `promo` to `group_id`.
    Returns True on success, False on failure.
    Logs result to the database.
    """
    promo_id   = promo["id"]
    text       = templates.build_promo_message(promo)
    keyboard   = build_promo_keyboard(promo)

    try:
        if promo["image_url"]:
            # Send as photo with caption
            await bot.send_photo(
                chat_id=group_id,
                photo=promo["image_url"],
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            # Text-only message
            await bot.send_message(
                chat_id=group_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )

        db.log_send(promo_id, group_id, "success")
        db.mark_promotion_sent(promo_id)
        logger.info("Promo %d sent to group %s ✅", promo_id, group_id)
        return True

    except TelegramError as e:
        db.log_send(promo_id, group_id, "failed")
        logger.error("Failed to send promo %d to %s: %s", promo_id, group_id, e)
        return False


# ─── BROADCAST ────────────────────────────────────────────────────────────────

async def broadcast_promotion(bot: Bot, promo, notify_admin_id: int = None) -> dict:
    """
    Send `promo` to ALL active groups.
    Respects rate limiting (SEND_DELAY_SECONDS between each group).
    Returns a summary dict: {sent, failed, skipped}.
    """
    groups = db.get_active_groups()
    sent = failed = skipped = 0

    for i, group in enumerate(groups):
        gid = group["group_id"]

        # Skip if same promo was sent to this group recently
        if db.was_recently_sent(promo["id"], gid):
            skipped += 1
            logger.debug("Skipping promo %d → group %s (recent duplicate)", promo["id"], gid)
            continue

        success = await send_promotion_to_group(bot, promo, gid)
        if success:
            sent += 1
        else:
            failed += 1

        # Rate limiting: pause between sends
        await asyncio.sleep(config.SEND_DELAY_SECONDS)

        # Extra pause between batches
        if (i + 1) % config.GROUP_BATCH_SIZE == 0:
            await asyncio.sleep(config.BATCH_DELAY_SECONDS)

    summary = {"sent": sent, "failed": failed, "skipped": skipped}

    if notify_admin_id:
        try:
            promo_title = promo["title"]
            msg = (
                f"📣 <b>Broadcast Complete</b>\n\n"
                f"🎬 Promo: <b>{promo_title}</b>\n"
                f"✅ Sent:    {sent}\n"
                f"❌ Failed:  {failed}\n"
                f"⏭️ Skipped: {skipped} (recent duplicate)"
            )
            await bot.send_message(notify_admin_id, msg, parse_mode="HTML")
        except TelegramError:
            pass  # Admin notification is non-critical

    return summary


# ─── NEXT PROMO PICKER (round-robin) ─────────────────────────────────────────

def get_next_promo():
    """
    Pick the next active promotion using a round-robin index stored in DB settings.
    Returns the promo row, or None if there are no active promotions.
    """
    promos = db.get_active_promotions()
    if not promos:
        return None

    current_index = int(db.get_setting("promo_index") or 0)
    # Clamp to valid range (promos may have been deleted)
    current_index = current_index % len(promos)
    promo = promos[current_index]

    # Advance index for next call
    next_index = (current_index + 1) % len(promos)
    db.set_setting("promo_index", str(next_index))

    return promo
